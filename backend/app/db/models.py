import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.database import Base

USERS_ID_FK = "users.id"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    credentials = relationship(
        "WebAuthnCredential", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    oauth_clients = relationship("OAuthClient", back_populates="owner")


class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"
    user_id = Column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK), nullable=False)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK), nullable=False)
    credential_id = Column(String, unique=True, nullable=False)
    public_key = Column(Text, nullable=False)
    sign_count = Column(Integer, default=0)
    transports = Column(JSONB)
    device_name = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    last_used = Column(DateTime)

    user = relationship("User", back_populates="credentials")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK), nullable=False)
    refresh_token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    ip_address = Column(String)
    user_agent = Column(String)

    user = relationship("User", back_populates="sessions")


class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String, unique=True, nullable=False)
    client_secret = Column(String, nullable=False)
    name = Column(String, nullable=False)
    redirect_uris = Column(JSONB, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK))
    scope = Column(String)
    owner_id = Column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK))
    created_at = Column(DateTime, default=datetime.now)

    owner = relationship("User", back_populates="oauth_clients")


class AuthorizationCode(Base):
    __tablename__ = "authorization_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, nullable=False)
    client_id = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey(USERS_ID_FK), nullable=False)
    redirect_uri = Column(String, nullable=False)
    scope = Column(String)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String, nullable=False, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey(USERS_ID_FK), nullable=True, index=True
    )
    ip_address = Column(String, index=True)
    user_agent = Column(String)
    resource = Column(String, index=True)
    action = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    details = Column(JSONB)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
