import base64
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, create_refresh_token
from app.core.config import settings
from app.core.logging import get_logger
from app.core.schemas import (
    LoginOptionsRequest,
    LoginVerification,
    RegistrationOptionsRequest,
    RegistrationVerification,
    TokenResponse,
)
from app.db.database import get_db
from app.db.models import Session as DBSession
from app.db.models import User
from app.services.security_service import BiometricSecurityValidator, SecurityService
from app.services.webauthn_service import WebAuthnService

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


@router.post("/register/options")
async def registration_options(
    request: RegistrationOptionsRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = http_request.client.host
    user_agent = http_request.headers.get("user-agent", "")

    # Security checks
    if SecurityService.is_rate_limited(client_ip, "registration"):
        await SecurityService.log_security_event(
            "RATE_LIMIT_EXCEEDED",
            None,
            client_ip,
            user_agent,
            {"action": "registration", "email": request.email},
            db,
            "WARNING",
        )
        raise HTTPException(status_code=429, detail="Too many registration attempts")

    # Check if user already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        await SecurityService.log_security_event(
            "DUPLICATE_REGISTRATION",
            None,
            client_ip,
            user_agent,
            {"email": request.email},
            db,
            "WARNING",
        )
        raise HTTPException(status_code=400, detail="User already exists")

    # Generate device fingerprint
    device_fingerprint = SecurityService.generate_device_fingerprint(
        dict(http_request.headers), client_ip
    )

    try:
        options = await WebAuthnService.generate_registration_options(
            request.email, request.username
        )

        # Store challenge with enhanced security metadata
        challenge_data = {
            "challenge": options["challenge"],
            "device_fingerprint": device_fingerprint,
            "ip_address": client_ip,
            "timestamp": datetime.now().isoformat(),
        }

        import json

        await redis_client.setex(
            f"reg_challenge:{request.email}", 300, json.dumps(challenge_data)
        )

        await SecurityService.log_security_event(
            "REGISTRATION_OPTIONS_GENERATED",
            None,
            client_ip,
            user_agent,
            {"email": request.email, "device_fingerprint": device_fingerprint},
            db,
        )

        return options

    except Exception as e:
        logger.error(f"Registration options generation failed: {e}")
        raise HTTPException(status_code=500, detail="Registration unavailable")


@router.post("/register/verify", response_model=TokenResponse)
async def registration_verify(
    request: RegistrationVerification,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = http_request.client.host
    user_agent = http_request.headers.get("user-agent", "")

    # Retrieve and validate challenge data
    challenge_data_str = await redis_client.get(f"reg_challenge:{request.email}")
    if not challenge_data_str:
        await SecurityService.log_security_event(
            "EXPIRED_CHALLENGE",
            None,
            client_ip,
            user_agent,
            {"email": request.email, "action": "registration"},
            db,
            "WARNING",
        )
        raise HTTPException(status_code=400, detail="Challenge expired")

    try:
        import json

        # Parse challenge data
        challenge_data = json.loads(challenge_data_str)
        challenge_b64 = challenge_data["challenge"]
        stored_fingerprint = challenge_data["device_fingerprint"]

        # Validate device consistency
        current_fingerprint = SecurityService.generate_device_fingerprint(
            dict(http_request.headers), client_ip
        )

        if current_fingerprint != stored_fingerprint:
            await SecurityService.log_security_event(
                "DEVICE_FINGERPRINT_MISMATCH",
                None,
                client_ip,
                user_agent,
                {
                    "email": request.email,
                    "expected": stored_fingerprint,
                    "actual": current_fingerprint,
                },
                db,
                "ERROR",
            )
            raise HTTPException(status_code=400, detail="Device validation failed")

        # Validate biometric data quality
        if not SecurityService.validate_biometric_quality(request.credential):
            await SecurityService.log_security_event(
                "POOR_BIOMETRIC_QUALITY",
                None,
                client_ip,
                user_agent,
                {"email": request.email},
                db,
                "WARNING",
            )
            raise HTTPException(
                status_code=400, detail="Biometric quality insufficient"
            )

        # Check for presentation attacks
        if BiometricSecurityValidator.detect_presentation_attack(request.credential):
            await SecurityService.log_security_event(
                "PRESENTATION_ATTACK_DETECTED",
                None,
                client_ip,
                user_agent,
                {"email": request.email},
                db,
                "CRITICAL",
            )
            raise HTTPException(status_code=400, detail="Security validation failed")

        # Create user
        username = request.email.split("@")[0]  # Generate username from email
        user = User(
            email=request.email,
            username=username,
            display_name=username,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()

        # Verify registration with WebAuthn
        challenge_bytes = base64.urlsafe_b64decode(
            challenge_b64 + "=" * (4 - len(challenge_b64) % 4)
        )

        verification = await WebAuthnService.verify_registration(
            request.credential, challenge_bytes, user, db
        )

        # Generate secure tokens
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        # Create secure session
        session = DBSession(
            user_id=user.id,
            refresh_token=refresh_token,
            expires_at=datetime.now()
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address=client_ip,
            user_agent=user_agent,
        )
        db.add(session)
        await db.commit()

        # Clean up challenge
        await redis_client.delete(f"reg_challenge:{request.email}")

        await SecurityService.log_security_event(
            "REGISTRATION_SUCCESS",
            str(user.id),
            client_ip,
            user_agent,
            {
                "email": request.email,
                "credential_id": verification.credential_id.hex()[:16],
            },
            db,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        await SecurityService.log_security_event(
            "REGISTRATION_FAILED",
            None,
            client_ip,
            user_agent,
            {"email": request.email, "error": str(e)},
            db,
            "ERROR",
        )
        logger.error(f"Registration verification failed: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")


@router.post("/login/options")
async def login_options(
    request: LoginOptionsRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = http_request.client.host
    user_agent = http_request.headers.get("user-agent", "")

    # Rate limiting check
    if SecurityService.is_rate_limited(client_ip, "authentication"):
        await SecurityService.log_security_event(
            "AUTH_RATE_LIMIT_EXCEEDED",
            None,
            client_ip,
            user_agent,
            {"identifier": request.identifier},
            db,
            "WARNING",
        )
        raise HTTPException(status_code=429, detail="Too many authentication attempts")

    # Find user by email or username
    from sqlalchemy import or_
    result = await db.execute(
        select(User).where(
            or_(User.email == request.identifier, User.username == request.identifier)
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        await SecurityService.log_security_event(
            "AUTH_USER_NOT_FOUND",
            None,
            client_ip,
            user_agent,
            {"identifier": request.identifier},
            db,
            "WARNING",
        )
        raise HTTPException(status_code=404, detail="User not found")

    # Check account lockout
    if await SecurityService.check_account_lockout(str(user.id), db):
        await SecurityService.log_security_event(
            "ACCOUNT_LOCKED",
            str(user.id),
            client_ip,
            user_agent,
            {"identifier": request.identifier, "email": user.email},
            db,
            "ERROR",
        )
        raise HTTPException(status_code=423, detail="Account temporarily locked")

    # Detect suspicious activity
    suspicious_activities = await SecurityService.detect_suspicious_activity(
        str(user.id), client_ip, user_agent, db
    )

    if suspicious_activities:
        await SecurityService.log_security_event(
            "SUSPICIOUS_ACTIVITY",
            str(user.id),
            client_ip,
            user_agent,
            {"activities": suspicious_activities},
            db,
            "WARNING",
        )

    try:
        options = await WebAuthnService.generate_authentication_options(user, db)

        # Generate device fingerprint
        device_fingerprint = SecurityService.generate_device_fingerprint(
            dict(http_request.headers), client_ip
        )

        # Store challenge with security metadata
        challenge_data = {
            "challenge": options["challenge"],
            "device_fingerprint": device_fingerprint,
            "ip_address": client_ip,
            "timestamp": datetime.now().isoformat(),
            "user_id": str(user.id),
        }

        import json

        await redis_client.setex(
            f"auth_challenge:{user.email}", 300, json.dumps(challenge_data)
        )

        await SecurityService.log_security_event(
            "AUTH_OPTIONS_GENERATED",
            str(user.id),
            client_ip,
            user_agent,
            {"identifier": request.identifier, "email": user.email, "suspicious_count": len(suspicious_activities)},
            db,
        )

        return options

    except Exception as e:
        await SecurityService.log_security_event(
            "AUTH_OPTIONS_FAILED",
            str(user.id),
            client_ip,
            user_agent,
            {"identifier": request.identifier, "email": user.email, "error": str(e)},
            db,
            "ERROR",
        )
        logger.error(f"Authentication options generation failed: {e}")
        raise HTTPException(status_code=500, detail="Authentication unavailable")


@router.post("/login/verify", response_model=TokenResponse)
async def login_verify(
    request: LoginVerification,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = http_request.client.host
    user_agent = http_request.headers.get("user-agent", "")

    # Find user first to get email for challenge lookup
    from sqlalchemy import or_
    result = await db.execute(
        select(User).where(
            or_(User.email == request.identifier, User.username == request.identifier)
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Retrieve and validate challenge data
    challenge_data_str = await redis_client.get(f"auth_challenge:{user.email}")
    if not challenge_data_str:
        await SecurityService.log_security_event(
            "AUTH_CHALLENGE_EXPIRED",
            None,
            client_ip,
            user_agent,
            {"identifier": request.identifier, "email": user.email},
            db,
            "WARNING",
        )
        raise HTTPException(status_code=400, detail="Challenge expired")

    try:
        # Parse challenge data
        import json

        challenge_data = json.loads(challenge_data_str)
        challenge_b64 = challenge_data["challenge"]
        stored_fingerprint = challenge_data["device_fingerprint"]
        stored_user_id = challenge_data["user_id"]

        # Validate user matches stored challenge
        if str(user.id) != stored_user_id:
            await SecurityService.log_security_event(
                "AUTH_USER_MISMATCH",
                stored_user_id,
                client_ip,
                user_agent,
                {"identifier": request.identifier, "email": user.email},
                db,
                "ERROR",
            )
            raise HTTPException(status_code=404, detail="Authentication failed")

        # Validate device consistency
        current_fingerprint = SecurityService.generate_device_fingerprint(
            dict(http_request.headers), client_ip
        )

        if current_fingerprint != stored_fingerprint:
            await SecurityService.log_security_event(
                "AUTH_DEVICE_MISMATCH",
                str(user.id),
                client_ip,
                user_agent,
                {"identifier": request.identifier, "email": user.email},
                db,
                "ERROR",
            )
            raise HTTPException(status_code=400, detail="Device validation failed")

        # Enhanced biometric validation
        if not BiometricSecurityValidator.validate_liveness(
            base64.b64decode(
                request.credential.get("response", {}).get("authenticatorData", "")
            )
        ):
            await SecurityService.log_security_event(
                "LIVENESS_CHECK_FAILED",
                str(user.id),
                client_ip,
                user_agent,
                {"identifier": request.identifier, "email": user.email},
                db,
                "ERROR",
            )
            raise HTTPException(status_code=400, detail="Biometric validation failed")

        # Check for presentation attacks
        if BiometricSecurityValidator.detect_presentation_attack(request.credential):
            await SecurityService.log_security_event(
                "AUTH_PRESENTATION_ATTACK",
                str(user.id),
                client_ip,
                user_agent,
                {"identifier": request.identifier, "email": user.email},
                db,
                "CRITICAL",
            )
            raise HTTPException(status_code=400, detail="Security validation failed")

        # Verify authentication with WebAuthn
        challenge_bytes = base64.urlsafe_b64decode(
            challenge_b64 + "=" * (4 - len(challenge_b64) % 4)
        )

        verification = await WebAuthnService.verify_authentication(
            request.credential, challenge_bytes, user, db
        )

        # Generate secure tokens
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        # Create secure session
        session = DBSession(
            user_id=user.id,
            refresh_token=refresh_token,
            expires_at=datetime.now()
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address=client_ip,
            user_agent=user_agent,
        )
        db.add(session)
        await db.commit()

        # Clean up challenge
        await redis_client.delete(f"auth_challenge:{user.email}")

        await SecurityService.log_security_event(
            "AUTHENTICATION_SUCCESS",
            str(user.id),
            client_ip,
            user_agent,
            {"identifier": request.identifier, "email": user.email, "sign_count": verification.new_sign_count},
            db,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    except HTTPException:
        raise
    except Exception as e:
        await SecurityService.log_security_event(
            "AUTHENTICATION_FAILED",
            None,
            client_ip,
            user_agent,
            {"identifier": request.identifier, "error": str(e)},
            db,
            "ERROR",
        )
        logger.error(f"Authentication verification failed: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
