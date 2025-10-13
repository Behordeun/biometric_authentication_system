from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["openid-connect"])


@router.get("/.well-known/openid-configuration")
async def openid_configuration():
    base_url = f"http://{settings.RP_ID}"
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth2/authorize",
        "token_endpoint": f"{base_url}/oauth2/token",
        "userinfo_endpoint": f"{base_url}/userinfo",
        "jwks_uri": f"{base_url}/.well-known/jwks.json",
        "response_types_supported": ["code", "token", "id_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["HS256"],
        "scopes_supported": ["openid", "profile", "email"],
    }
