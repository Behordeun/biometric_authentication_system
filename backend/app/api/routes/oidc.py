from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["openid-connect"])


@router.get("/.well-known/openid-configuration")
async def openid_configuration():
    return {
        "issuer": f"http://{settings.RP_ID}",
        "authorization_endpoint": f"http://{settings.RP_ID}/oauth2/authorize",
        "token_endpoint": f"http://{settings.RP_ID}/oauth2/token",
        "userinfo_endpoint": f"http://{settings.RP_ID}/userinfo",
        "jwks_uri": f"http://{settings.RP_ID}/.well-known/jwks.json",
        "response_types_supported": ["code", "token", "id_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["HS256"],
        "scopes_supported": ["openid", "profile", "email"],
    }
