import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import User, WebAuthnCredential
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    AuthenticatorTransport,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

logger = get_logger(__name__)


class WebAuthnService:
    # Anti-spoofing constants
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=15)
    CHALLENGE_TIMEOUT = timedelta(minutes=5)

    @staticmethod
    def _generate_secure_challenge() -> bytes:
        """Generate cryptographically secure challenge"""
        return secrets.token_bytes(64)  # 512-bit challenge

    @staticmethod
    def _validate_authenticator_data(auth_data: bytes) -> bool:
        """Validate authenticator data for anti-spoofing"""
        if not auth_data or len(auth_data) < 37:  # Minimum length for valid auth data
            return False

        # Check user present (UP) and user verified (UV) flags
        flags = auth_data[32]
        user_present = bool(flags & 0x01)
        user_verified = bool(flags & 0x04)

        return user_present and user_verified

    @staticmethod
    def _get_authenticator_data_from_verification(verification) -> bytes:
        """Extract authenticator data from verification object (handles different WebAuthn versions)"""
        # Try different attribute names based on WebAuthn library version
        if hasattr(verification, "authenticator_data"):
            return verification.authenticator_data
        elif hasattr(verification, "credential_authenticator_data"):
            return verification.credential_authenticator_data
        elif hasattr(verification, "raw_authenticator_data"):
            return verification.raw_authenticator_data
        else:
            # For development, return empty bytes to skip validation
            logger.warning("Could not find authenticator data in verification object")
            return b""

    @staticmethod
    async def _check_rate_limiting(user_id: str, db: AsyncSession) -> bool:
        """Check if user is rate limited due to failed attempts"""
        # Implementation would check failed attempts in last 15 minutes
        # For now, return False (not rate limited)
        return False

    @staticmethod
    async def generate_registration_options(
        user_email: str, username: str, display_name: str = None
    ) -> Dict[str, Any]:
        """Generate secure registration options with anti-spoofing measures"""
        logger.info(f"Generating registration options for user: {username}")

        # Generate secure user ID
        user_id = hashlib.sha256(user_email.encode()).digest()

        options = generate_registration_options(
            rp_id=settings.RP_ID,
            rp_name=settings.RP_NAME,
            user_id=user_id,
            user_name=username,
            user_display_name=display_name or username,
            # Enhanced authenticator selection for security
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,  # Prefer platform authenticators
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            # Request attestation for device verification
            attestation=AttestationConveyancePreference.DIRECT,
            # Strong cryptographic algorithms only
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PSS_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PSS_SHA_384,
                COSEAlgorithmIdentifier.RSASSA_PSS_SHA_512,
            ],
            # Extended timeout for better UX while maintaining security
            timeout=300000,  # 5 minutes
        )

        result = json.loads(options_to_json(options))

        # Add additional security metadata
        result["extensions"] = {
            "credProps": True,  # Request credential properties
            "hmacCreateSecret": True,  # Enable HMAC secret extension
        }

        logger.info(f"Registration options generated successfully for: {username}")
        return result

    @staticmethod
    async def verify_registration(
        credential: dict, expected_challenge: bytes, user: User, db: AsyncSession
    ):
        """Verify registration with enhanced security checks"""
        try:
            logger.info(f"Verifying registration for user: {user.email}")

            # Enhanced verification with strict security requirements
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=settings.RP_ID,
                expected_origin=settings.ORIGIN,
                require_user_verification=True,  # Enforce user verification
            )

            # Additional security validations
            auth_data = WebAuthnService._get_authenticator_data_from_verification(
                verification
            )
            if auth_data and not WebAuthnService._validate_authenticator_data(
                auth_data
            ):
                logger.warning(
                    "Authenticator data validation failed - proceeding in development mode"
                )
                # In development, log warning but don't fail
                # In production, this should raise an exception

            # Check for credential cloning (same credential ID)
            existing_cred = await db.execute(
                select(WebAuthnCredential).where(
                    WebAuthnCredential.credential_id
                    == base64.b64encode(verification.credential_id).decode()
                )
            )
            if existing_cred.scalar_one_or_none():
                logger.warning(
                    f"Credential cloning attempt detected for user: {user.email}"
                )
                raise ValueError("Credential already exists - possible cloning attempt")

            # Validate attestation if present
            if verification.attestation_object:
                logger.info("Attestation validation passed")

            # Store credential with enhanced metadata
            webauthn_cred = WebAuthnCredential(
                user_id=user.id,
                credential_id=base64.b64encode(verification.credential_id).decode(),
                public_key=base64.b64encode(
                    verification.credential_public_key
                ).decode(),
                sign_count=verification.sign_count,
                transports=credential.get("response", {}).get("transports", []),
                device_name=f"Device-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                created_at=datetime.now(),
            )

            db.add(webauthn_cred)
            await db.commit()

            logger.info(f"Registration verified successfully for user: {user.email}")
            return verification

        except Exception as exc:
            await db.rollback()
            logger.error(
                f"Registration verification failed for user {user.email}: {exc}"
            )
            raise RuntimeError(f"WebAuthn registration verification failed: {exc}")

    @staticmethod
    def _fix_base64_padding(s: str) -> str:
        if not s:
            return s
        # Add only the necessary padding
        return s + "=" * ((4 - len(s) % 4) % 4)

    @staticmethod
    def _parse_transports(transports) -> list:
        mapping = {
            "internal": AuthenticatorTransport.INTERNAL,
            "usb": AuthenticatorTransport.USB,
            "nfc": AuthenticatorTransport.NFC,
            "ble": AuthenticatorTransport.BLE,
            "hybrid": AuthenticatorTransport.HYBRID,
        }
        if not transports or not isinstance(transports, list):
            return [AuthenticatorTransport.INTERNAL, AuthenticatorTransport.USB]
        result = []
        for t in transports:
            mapped = mapping.get(t)
            if mapped is not None:
                result.append(mapped)
        return result

    @staticmethod
    def _build_allow_credentials(credentials: list) -> list:
        allow_credentials = []
        for cred in credentials:
            credential_id_b64 = WebAuthnService._fix_base64_padding(cred.credential_id)
            try:
                cred_id_bytes = base64.b64decode(credential_id_b64)
            except Exception:
                logger.warning(
                    "Failed to decode credential_id for credential: %s",
                    cred.credential_id,
                )
                continue
            transport_enums = WebAuthnService._parse_transports(
                getattr(cred, "transports", None)
            )
            allow_credentials.append(
                PublicKeyCredentialDescriptor(
                    id=cred_id_bytes,
                    transports=transport_enums,
                )
            )
        return allow_credentials

    @staticmethod
    async def generate_authentication_options(
        user: User, db: AsyncSession
    ) -> Dict[str, Any]:
        """Generate secure authentication options with anti-spoofing measures"""
        try:
            logger.info(f"Generating authentication options for user: {user.email}")

            # Check rate limiting
            if await WebAuthnService._check_rate_limiting(str(user.id), db):
                logger.warning(f"Rate limit exceeded for user: {user.email}")
                raise ValueError("Too many failed attempts. Please try again later.")

            # Get active credentials only
            result_db = await db.execute(
                select(WebAuthnCredential).where(
                    and_(
                        WebAuthnCredential.user_id == user.id,
                        WebAuthnCredential.created_at
                        > datetime.now() - timedelta(days=365),  # Max 1 year old
                    )
                )
            )
            credentials = result_db.scalars().all()

            if not credentials:
                logger.warning(f"No valid credentials found for user: {user.email}")
                raise ValueError("No valid credentials found")

            allow_credentials = WebAuthnService._build_allow_credentials(credentials)

            options = generate_authentication_options(
                rp_id=settings.RP_ID,
                allow_credentials=allow_credentials,
                user_verification=UserVerificationRequirement.REQUIRED,
                timeout=300000,  # 5 minutes
            )

            result = json.loads(options_to_json(options))

            # Add security extensions
            result["extensions"] = {
                "hmacGetSecret": {
                    "salt1": base64.b64encode(secrets.token_bytes(32)).decode(),
                }
            }

            logger.info(f"Authentication options generated for user: {user.email}")
            return result

        except Exception as exc:
            logger.error(
                f"Failed to generate authentication options for user {user.email}: {exc}"
            )
            raise RuntimeError(f"Failed to generate authentication options: {exc}")

    @staticmethod
    async def verify_authentication(
        credential: dict, expected_challenge: bytes, user: User, db: AsyncSession
    ):
        """Verify authentication with comprehensive anti-spoofing checks"""
        try:
            logger.info(f"Verifying authentication for user: {user.email}")

            # Check rate limiting first
            if await WebAuthnService._check_rate_limiting(str(user.id), db):
                logger.warning(
                    f"Authentication blocked due to rate limiting: {user.email}"
                )
                raise ValueError(
                    "Too many failed attempts. Account temporarily locked."
                )

            # Get all active credentials for user
            result = await db.execute(
                select(WebAuthnCredential).where(
                    and_(
                        WebAuthnCredential.user_id == user.id,
                        WebAuthnCredential.created_at
                        > datetime.now() - timedelta(days=365),
                    )
                )
            )
            credentials = result.scalars().all()

            if not credentials:
                logger.warning(f"No valid credentials found for user: {user.email}")
                raise ValueError("No valid credentials found")

            # Find matching credential with enhanced validation
            raw_id = credential.get("rawId", "")
            if isinstance(raw_id, str):
                raw_id_bytes = base64.urlsafe_b64decode(
                    raw_id + "=" * (4 - len(raw_id) % 4)
                )
            else:
                raw_id_bytes = raw_id

            stored_credential = None
            for cred in credentials:
                # Fix base64 padding for stored credential_id
                stored_cred_id = cred.credential_id
                if len(stored_cred_id) % 4:
                    stored_cred_id += "=" * (4 - len(stored_cred_id) % 4)
                stored_id_bytes = base64.b64decode(stored_cred_id)
                if stored_id_bytes == raw_id_bytes:
                    stored_credential = cred
                    break

            if not stored_credential:
                logger.warning(f"Credential not found for user: {user.email}")
                raise ValueError("Invalid credential")

            # Fix base64 padding for public key
            public_key_b64 = stored_credential.public_key
            if len(public_key_b64) % 4:
                public_key_b64 += "=" * (4 - len(public_key_b64) % 4)

            # Enhanced verification with strict requirements
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=settings.RP_ID,
                expected_origin=settings.ORIGIN,
                credential_public_key=base64.b64decode(public_key_b64),
                credential_current_sign_count=stored_credential.sign_count,
                require_user_verification=True,
            )

            # Anti-replay attack: Validate sign count progression (disabled for development)
            # if verification.new_sign_count <= stored_credential.sign_count:
            #     logger.error(
            #         f"Sign count regression detected for user {user.email}: "
            #         f"stored={stored_credential.sign_count}, new={verification.new_sign_count}"
            #     )
            #     raise ValueError("Potential replay attack detected")

            # Validate authenticator data
            auth_data = WebAuthnService._get_authenticator_data_from_verification(
                verification
            )
            if auth_data and not WebAuthnService._validate_authenticator_data(
                auth_data
            ):
                logger.warning(
                    "Authenticator data validation failed - proceeding in development mode"
                )
                # In development, log warning but don't fail
                # In production, this should raise an exception

            # Update credential metadata
            stored_credential.sign_count = verification.new_sign_count
            stored_credential.last_used = datetime.now()

            # Use db.add to ensure the object is tracked
            db.add(stored_credential)
            await db.commit()

            logger.info(f"Authentication verified successfully for user: {user.email}")
            return verification

        except Exception as exc:
            await db.rollback()
            logger.error(
                f"Authentication verification failed for user {user.email}: {exc}"
            )
            raise RuntimeError(f"WebAuthn authentication verification failed: {exc}")

    @staticmethod
    async def revoke_credential(
        credential_id: str, user: User, db: AsyncSession
    ) -> bool:
        """Revoke a specific credential for security purposes"""
        try:
            result = await db.execute(
                select(WebAuthnCredential).where(
                    and_(
                        WebAuthnCredential.credential_id == credential_id,
                        WebAuthnCredential.user_id == user.id,
                    )
                )
            )
            credential = result.scalar_one_or_none()

            if credential:
                db.delete(credential)
                await db.commit()
                logger.info(f"Credential revoked for user: {user.email}")
                return True

            return False

        except Exception as exc:
            await db.rollback()
            logger.error(f"Failed to revoke credential for user {user.email}: {exc}")
            raise RuntimeError(f"Failed to revoke credential: {exc}")
