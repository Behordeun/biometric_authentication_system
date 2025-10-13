from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import AuditLog

logger = get_logger(__name__)


class AuditLogger:
    """Audit logging for security-critical events"""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        event_type: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: str = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log audit event to database and application logs"""

        # Log to application logger
        log_extra = {
            "user_id": user_id,
            "ip_address": ip_address,
            "action": action,
            "resource": resource,
            "status": status,
            "extra_data": details,
        }

        logger.info(f"Audit: {event_type} - {action} on {resource}", extra=log_extra)

        # Store in database
        audit_entry = AuditLog(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource=resource,
            action=action,
            status=status,
            details=details,
            timestamp=datetime.now(),
        )

        db.add(audit_entry)
        await db.commit()

        return audit_entry


# Convenience methods for common audit events
async def log_login_attempt(
    db: AsyncSession,
    username: str,
    ip_address: str,
    user_agent: str,
    success: bool,
    user_id: Optional[int] = None,
):
    await AuditLogger.log_event(
        db=db,
        event_type="authentication",
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        resource="user",
        action="login",
        status="success" if success else "failure",
        details={"username": username},
    )


async def log_registration(
    db: AsyncSession,
    user_id: int,
    username: str,
    ip_address: str,
    user_agent: str,
):
    await AuditLogger.log_event(
        db=db,
        event_type="user_management",
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        resource="user",
        action="register",
        status="success",
        details={"username": username},
    )


async def log_credential_added(
    db: AsyncSession,
    user_id: int,
    credential_type: str,
    ip_address: str,
    user_agent: str,
):
    await AuditLogger.log_event(
        db=db,
        event_type="credential_management",
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        resource="credential",
        action="add",
        status="success",
        details={"credential_type": credential_type},
    )


async def log_token_issued(
    db: AsyncSession,
    user_id: int,
    token_type: str,
    ip_address: str,
):
    await AuditLogger.log_event(
        db=db,
        event_type="token_management",
        user_id=user_id,
        ip_address=ip_address,
        resource="token",
        action="issue",
        status="success",
        details={"token_type": token_type},
    )


async def log_security_event(
    db: AsyncSession,
    event_type: str,
    ip_address: str,
    details: Dict[str, Any],
    user_id: Optional[int] = None,
):
    await AuditLogger.log_event(
        db=db,
        event_type="security",
        user_id=user_id,
        ip_address=ip_address,
        resource="system",
        action=event_type,
        status="alert",
        details=details,
    )
