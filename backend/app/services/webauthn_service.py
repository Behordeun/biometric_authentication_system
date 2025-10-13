try:
    import base64
    import json
except ImportError as e:
    raise ImportError(f"Failed to import a required module: {e}")

from app.core.config import settings
from app.db.models import User, WebAuthnCredential
from sqlalchemy import select
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
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)


class WebAuthnService:
    @staticmethod
    async def generate_registration_options(user_email: str, username: str):
        options = generate_registration_options(
            rp_id=settings.RP_ID,
            rp_name=settings.RP_NAME,
            user_id=user_email.encode(),
            user_name=username,
            user_display_name=username,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
            ],
        )
        return json.loads(options_to_json(options))

    @staticmethod
    async def verify_registration(
        credential: dict, expected_challenge: bytes, user: User, db: AsyncSession
    ):
        try:
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=settings.RP_ID,
                expected_origin=settings.ORIGIN,
            )

            webauthn_cred = WebAuthnCredential(
                user_id=user.id,
                credential_id=base64.b64encode(verification.credential_id).decode(),
                public_key=base64.b64encode(verification.credential_public_key).decode(),
                sign_count=verification.sign_count,
                transports=credential.get("transports", []),
            )
            db.add(webauthn_cred)
            await db.commit()
            return verification
        except Exception as exc:
            await db.rollback()
            raise RuntimeError(f"WebAuthn registration verification failed: {exc}")
    @staticmethod
    async def generate_authentication_options(user: User, db: AsyncSession):
        try:
            result = await db.execute(
                select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id)
            )
            credentials = result.scalars().all()

            allow_credentials = [
                PublicKeyCredentialDescriptor(id=base64.b64decode(cred.credential_id))
                for cred in credentials
            ]

            options = generate_authentication_options(
                rp_id=settings.RP_ID,
                allow_credentials=allow_credentials,
                user_verification=UserVerificationRequirement.REQUIRED,
            )
            return json.loads(options_to_json(options))
        except Exception as exc:
            # Optionally log the error here
            raise RuntimeError(f"Failed to generate authentication options: {exc}")
    @staticmethod
    async def verify_authentication(
        credential: dict, expected_challenge: bytes, user: User, db: AsyncSession
    ):
        try:
            # Get all credentials for user
            result = await db.execute(
                select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id)
            )
            credentials = result.scalars().all()
            if not credentials:
                raise ValueError("No credentials found for user")

            # Try to find matching credential by comparing rawId
            raw_id = credential.get("rawId", "")
            if isinstance(raw_id, str):
                raw_id_bytes = base64.urlsafe_b64decode(
                    raw_id + "=" * (4 - len(raw_id) % 4)
                )
            else:
                raw_id_bytes = raw_id

            stored_credential = None
            for cred in credentials:
                stored_id_bytes = base64.b64decode(cred.credential_id)
                if stored_id_bytes == raw_id_bytes:
                    stored_credential = cred
                    break

            if not stored_credential:
                raise ValueError("Credential not found")

            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=settings.RP_ID,
                expected_origin=settings.ORIGIN,
                credential_public_key=base64.b64decode(stored_credential.public_key),
                credential_current_sign_count=stored_credential.sign_count,
            )

            stored_credential.sign_count = verification.new_sign_count
            await db.commit()
            return verification
        except Exception as exc:
            await db.rollback()
            raise RuntimeError(f"WebAuthn authentication verification failed: {exc}")
