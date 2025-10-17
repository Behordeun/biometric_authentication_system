from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    display_name: Optional[str] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    display_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime


class RegistrationOptionsRequest(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    username: str
    email: EmailStr


class RegistrationVerification(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    username: str
    email: EmailStr
    credential: dict

    @classmethod
    def __get_validators__(cls):
        yield from super().__get_validators__()
        yield cls.validate_credential

    @staticmethod
    def validate_credential(value):
        if not isinstance(value, dict):
            raise ValueError("credential must be a dictionary")
        return value


class LoginOptionsRequest(BaseModel):
    identifier: str  # Can be email or username


class LoginVerification(BaseModel):
    identifier: str  # Can be email or username
    credential: dict


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class OAuthClientCreate(BaseModel):
    name: str
    redirect_uris: List[str]
    grant_types: List[str]
    scope: Optional[str] = None


class OAuthClientResponse(BaseModel):
    id: UUID
    client_id: str
    client_secret: str
    name: str
    redirect_uris: List[str]
    grant_types: List[str]
    scope: Optional[str]
