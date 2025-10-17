"""
Advanced Security Service for Anti-Spoofing and Identity Protection
"""

import hashlib
import hmac
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from ipaddress import ip_network
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import AuditLog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class SecurityService:
    """Advanced security service with anti-spoofing and fraud detection"""

    # Rate limiting configuration
    RATE_LIMITS = {
        "registration": {"attempts": 3, "window": 3600},  # 3 attempts per hour
        "authentication": {"attempts": 5, "window": 900},  # 5 attempts per 15 minutes
        "failed_auth": {"attempts": 5, "window": 3600},  # 10 failed auths per hour
    }

    # Suspicious activity thresholds
    SUSPICIOUS_THRESHOLDS = {
        "rapid_requests": 10,  # requests per minute
        "multiple_devices": 5,  # different user agents per hour
        "geographic_anomaly": 1000,  # km distance threshold
    }

    # In-memory rate limiting (use Redis in production)
    _rate_limit_cache: Dict[str, List[float]] = defaultdict(list)
    _device_fingerprints: Dict[str, Dict] = {}

    @staticmethod
    def generate_device_fingerprint(
        request_headers: Dict[str, str], ip_address: str
    ) -> str:
        """Generate unique device fingerprint for tracking"""
        fingerprint_data = {
            "user_agent": request_headers.get("user-agent", ""),
            "accept_language": request_headers.get("accept-language", ""),
            "accept_encoding": request_headers.get("accept-encoding", ""),
            "ip_subnet": str(ip_network(f"{ip_address}/24", strict=False)),
        }

        fingerprint_string = "|".join(
            f"{k}:{v}" for k, v in sorted(fingerprint_data.items())
        )
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]

    @staticmethod
    def is_rate_limited(identifier: str, action: str) -> bool:
        """Check if action is rate limited"""
        if action not in SecurityService.RATE_LIMITS:
            return False

        config = SecurityService.RATE_LIMITS[action]
        current_time = time.time()
        window_start = current_time - config["window"]

        # Clean old entries
        cache_key = f"{identifier}:{action}"
        SecurityService._rate_limit_cache[cache_key] = [
            timestamp
            for timestamp in SecurityService._rate_limit_cache[cache_key]
            if timestamp > window_start
        ]

        # Check if limit exceeded
        if len(SecurityService._rate_limit_cache[cache_key]) >= config["attempts"]:
            logger.warning(f"Rate limit exceeded for {identifier} on action {action}")
            return True

        # Record this attempt
        SecurityService._rate_limit_cache[cache_key].append(current_time)
        return False

    @staticmethod
    async def detect_suspicious_activity(
        user_id: str, ip_address: str, user_agent: str, db: AsyncSession
    ) -> List[str]:
        """Detect suspicious activity patterns"""
        warnings = []
        current_time = datetime.now()

        # Check for rapid requests
        recent_logs = await db.execute(
            select(AuditLog).where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.timestamp > current_time - timedelta(minutes=1),
                )
            )
        )

        if (
            len(recent_logs.scalars().all())
            > SecurityService.SUSPICIOUS_THRESHOLDS["rapid_requests"]
        ):
            warnings.append("Rapid request pattern detected")

        # Check for multiple devices
        device_logs = await db.execute(
            select(AuditLog.user_agent)
            .where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.timestamp > current_time - timedelta(hours=1),
                )
            )
            .distinct()
        )

        unique_agents = len(device_logs.scalars().all())
        if unique_agents > SecurityService.SUSPICIOUS_THRESHOLDS["multiple_devices"]:
            warnings.append(f"Multiple devices detected: {unique_agents}")

        # Check for geographic anomalies (simplified)
        recent_ips = await db.execute(
            select(AuditLog.ip_address)
            .where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.timestamp > current_time - timedelta(hours=24),
                )
            )
            .distinct()
        )

        ip_list = recent_ips.scalars().all()
        if len(ip_list) > 3:  # More than 3 different IPs in 24h
            warnings.append("Multiple IP addresses detected")

        return warnings

    @staticmethod
    def validate_request_integrity(
        request_data: Dict, signature: str, timestamp: str
    ) -> bool:
        """Validate request integrity using HMAC"""
        try:
            # Check timestamp freshness (5 minute window)
            request_time = datetime.fromisoformat(timestamp)
            if abs((datetime.now() - request_time).total_seconds()) > 300:
                logger.warning("Request timestamp outside acceptable window")
                return False

            # Verify HMAC signature
            message = f"{timestamp}:{sorted(request_data.items())}"
            expected_signature = hmac.new(
                settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"Request integrity validation failed: {e}")
            return False

    @staticmethod
    async def check_credential_reuse(
        credential_id: str, user_id: str, db: AsyncSession
    ) -> bool:
        """Check if credential is being reused across accounts"""
        from app.db.models import WebAuthnCredential

        result = await db.execute(
            select(WebAuthnCredential).where(
                and_(
                    WebAuthnCredential.credential_id == credential_id,
                    WebAuthnCredential.user_id != user_id,
                )
            )
        )

        if result.scalar_one_or_none():
            logger.error(f"Credential reuse detected: {credential_id}")
            return True

        return False

    @staticmethod
    def generate_secure_session_token() -> str:
        """Generate cryptographically secure session token"""
        return secrets.token_urlsafe(64)

    @staticmethod
    def hash_sensitive_data(data: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash sensitive data with salt"""
        if salt is None:
            salt = secrets.token_hex(32)

        hashed = hashlib.pbkdf2_hmac(
            "sha256", data.encode(), salt.encode(), 100000  # 100k iterations
        )

        return hashed.hex(), salt

    @staticmethod
    async def log_security_event(
        event_type: str,
        user_id: Optional[str],
        ip_address: str,
        user_agent: str,
        details: Dict,
        db: AsyncSession,
        severity: str = "INFO",
    ):
        """Log security events for monitoring"""
        try:
            audit_log = AuditLog(
                event_type=f"SECURITY_{event_type}",
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                resource="security",
                action=event_type,
                status=severity,
                details=details,
                timestamp=datetime.now(),
            )

            db.add(audit_log)
            await db.commit()

            if severity in ["ERROR", "CRITICAL"]:
                logger.error(f"Security event: {event_type} - {details}")
            else:
                logger.info(f"Security event: {event_type}")

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    @staticmethod
    async def check_account_lockout(user_id: str, db: AsyncSession) -> bool:
        """Check if account should be locked due to suspicious activity"""
        current_time = datetime.now()

        # Count failed authentication attempts in last hour
        failed_attempts = await db.execute(
            select(func.count(AuditLog.id)).where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.action == "authentication",
                    AuditLog.status == "FAILED",
                    AuditLog.timestamp > current_time - timedelta(hours=1),
                )
            )
        )

        count = failed_attempts.scalar()
        if count >= 10:  # 10 failed attempts in 1 hour
            logger.warning(f"Account lockout triggered for user: {user_id}")
            return True

        return False

    @staticmethod
    def validate_biometric_quality(biometric_data: Dict) -> bool:
        """Validate biometric data quality to prevent spoofing"""
        # This would integrate with actual biometric quality assessment
        # For now, basic validation for WebAuthn credential structure

        # Check if it's a valid WebAuthn credential
        if not isinstance(biometric_data, dict):
            return False

        # Check for basic WebAuthn credential structure
        if "id" not in biometric_data or "response" not in biometric_data:
            return False

        response = biometric_data.get("response", {})
        if not isinstance(response, dict):
            return False

        # For development, be more lenient
        return True

    @staticmethod
    async def detect_anomalous_behavior(
        user_id: str, current_request: Dict, db: AsyncSession
    ) -> List[str]:
        """Detect anomalous user behavior patterns"""
        anomalies = []

        # Get user's historical behavior
        historical_data = await db.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.timestamp > datetime.now() - timedelta(days=30),
                )
            )
            .order_by(AuditLog.timestamp.desc())
            .limit(100)
        )

        logs = historical_data.scalars().all()

        if not logs:
            return anomalies

        # Analyze timing patterns
        current_hour = datetime.now().hour
        historical_hours = [log.timestamp.hour for log in logs]

        if historical_hours and current_hour not in historical_hours:
            anomalies.append("Unusual access time detected")

        # Analyze IP patterns
        current_ip = current_request.get("ip_address")
        historical_ips = [log.ip_address for log in logs if log.ip_address]

        if current_ip and current_ip not in historical_ips:
            anomalies.append("New IP address detected")

        return anomalies


class BiometricSecurityValidator:
    """Specialized validator for biometric security"""

    @staticmethod
    def validate_liveness(authenticator_data: bytes) -> bool:
        """Validate biometric liveness indicators"""
        if len(authenticator_data) < 37:
            return False

        # Check user verification flag (UV bit)
        flags = authenticator_data[32]
        user_verified = bool(flags & 0x04)

        if not user_verified:
            logger.warning("Biometric liveness check failed - UV flag not set")
            return False

        return True

    @staticmethod
    def detect_presentation_attack(credential_data: Dict) -> bool:
        """Detect presentation attacks (spoofing attempts)"""
        # For development, be more lenient with validation
        # In production, this would have more sophisticated checks

        if not isinstance(credential_data, dict):
            return True  # Suspicious

        # Basic structure check
        if "response" not in credential_data:
            return True  # Suspicious

        # For development, assume legitimate if basic structure is present
        return False  # Appears legitimate

    @staticmethod
    async def validate_device_integrity(
        device_fingerprint: str, user_id: str, db: AsyncSession
    ) -> bool:
        """Validate device integrity and detect device spoofing"""
        # Check if device fingerprint has been seen before for this user
        recent_logs = await db.execute(
            select(AuditLog).where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.details.contains(
                        {"device_fingerprint": device_fingerprint}
                    ),
                    AuditLog.timestamp > datetime.now() - timedelta(days=30),
                )
            )
        )

        if recent_logs.scalar_one_or_none():
            return True  # Known device

        # New device - additional validation required
        logger.info(f"New device detected for user: {user_id}")
        return False
