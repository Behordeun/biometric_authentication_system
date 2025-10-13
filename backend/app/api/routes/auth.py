import base64
from datetime import datetime, timedelta, timezone

import aioredis as redis
from app.core.auth import create_access_token, create_refresh_token
from app.core.config import settings
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
from app.services.webauthn_service import WebAuthnService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["authentication"])
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


@router.post("/register/options")
async def registration_options(
    request: RegistrationOptionsRequest, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")

    options = await WebAuthnService.generate_registration_options(
        request.email, request.username
    )
    await redis_client.setex(
        f"reg_challenge:{request.email}", 300, options["challenge"]
    )
    return options


@router.post("/register/verify", response_model=TokenResponse)
async def registration_verify(
    request: RegistrationVerification, db: AsyncSession = Depends(get_db)
):
    challenge_b64 = await redis_client.get(f"reg_challenge:{request.email}")
    if not challenge_b64:
        raise HTTPException(status_code=400, detail="Challenge expired")

    user = User(email=request.email, username=request.email.split("@")[0])
    db.add(user)
    await db.flush()

    challenge_bytes = base64.urlsafe_b64decode(
        challenge_b64 + "=" * (4 - len(challenge_b64) % 4)
    )
    await WebAuthnService.verify_registration(
        request.credential, challenge_bytes, user, db
    )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    session = DBSession(
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login/options")
async def login_options(
    request: LoginOptionsRequest, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    options = await WebAuthnService.generate_authentication_options(user, db)
    await redis_client.setex(
        f"auth_challenge:{request.email}", 300, options["challenge"]
    )
    return options


@router.post("/login/verify", response_model=TokenResponse)
async def login_verify(request: LoginVerification, db: AsyncSession = Depends(get_db)):
    challenge_b64 = await redis_client.get(f"auth_challenge:{request.email}")
    if not challenge_b64:
        raise HTTPException(status_code=400, detail="Challenge expired")

    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    challenge_bytes = base64.urlsafe_b64decode(
        challenge_b64 + "=" * (4 - len(challenge_b64) % 4)
    )
    await WebAuthnService.verify_authentication(
        request.credential, challenge_bytes, user, db
    )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    session = DBSession(
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
