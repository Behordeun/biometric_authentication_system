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
    email: EmailStr
    username: str
    display_name: Optional[str] = None


class RegistrationVerification(BaseModel):
    email: EmailStr
    credential: dict


class LoginOptionsRequest(BaseModel):
    email: EmailStr


class LoginVerification(BaseModel):
    email: EmailStr
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
