from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.db.models import AuditLog
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class AuditLogger:
    """Audit logging for security-critical events"""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        event_type: str,
        *,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log audit event to database and application logs.

        Args:
            db (AsyncSession): Database session.
            event_type (str): Type of the event.
            user_id (Optional[int], optional): ID of the user. Defaults to None.
            ip_address (Optional[str], optional): IP address of the user. Defaults to None.
            user_agent (Optional[str], optional): User agent string. Defaults to None.
            resource (Optional[str], optional): Resource affected. Defaults to None.
            action (Optional[str], optional): Action performed. Defaults to None.
            status (str, optional): Status of the event. Defaults to "success".
            details (Optional[Dict[str, Any]], optional): Additional event details. Defaults to None.
        """

        # Log to application logger
        log_extra = {
            "user_id": user_id,
            "ip_address": ip_address,
            "action": action,
            "resource": resource,
            "status": status,
            "extra_data": details,
        }

        logger.info(f"Audit: {event_type} - {action} on {resource} | Context: {log_extra}")

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
            timestamp=datetime.now(timezone.utc),
        )

        db.add(audit_entry)
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to commit audit log: {e}", exc_info=True)
            await db.rollback()
            raise

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
    try:
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
    except Exception as e:
        logger.error(f"Failed to log login attempt audit event: {e}", exc_info=True)


async def log_registration(
    db: AsyncSession,
    user_id: int,
    username: str,
    ip_address: str,
    user_agent: str,
):
    try:
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
    except Exception as e:
        logger.error(f"Failed to log registration audit event: {e}", exc_info=True)


async def log_credential_added(
    db: AsyncSession,
    user_id: int,
    credential_type: str,
    ip_address: str,
    user_agent: str,
):
    try:
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
    except Exception as e:
        logger.error(f"Failed to log credential added audit event: {e}", exc_info=True)


async def log_token_issued(
    db: AsyncSession,
    user_id: int,
    token_type: str,
    ip_address: str,
):
    try:
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
    except Exception as e:
        logger.error(f"Failed to log token issued audit event: {e}", exc_info=True)


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
