"""
Security Middleware for Enhanced Protection
"""

import time
from typing import Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.services.security_service import SecurityService

logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced security middleware with anti-spoofing protection"""

    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        try:
            # Security headers validation
            await self._validate_security_headers(request)

            # Request size validation
            await self._validate_request_size(request)

            # Rate limiting (basic IP-based)
            await self._check_global_rate_limit(request)

            # Process request
            response = await call_next(request)

            # Add security headers to response
            self._add_security_headers(response)

            # Log request metrics
            process_time = time.time() - start_time
            await self._log_request_metrics(request, response, process_time)

            return response

        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return JSONResponse(
                status_code=500, content={"detail": "Internal security error"}
            )

    async def _validate_security_headers(self, request: Request):
        """Validate required security headers"""
        # Check for required headers in production
        if (
            request.url.scheme != "https"
            and request.headers.get("host") != "localhost:8000"
        ):
            logger.warning(f"Insecure connection attempt from {request.client.host}")
            # In production, reject non-HTTPS requests
            # raise HTTPException(status_code=400, detail="HTTPS required")

        # Validate Content-Type for POST requests
        if request.method == "POST":
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                logger.warning(f"Invalid content type: {content_type}")
                raise HTTPException(status_code=400, detail="Invalid content type")

    async def _validate_request_size(self, request: Request):
        """Validate request size to prevent DoS attacks"""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            logger.warning(
                f"Request too large: {content_length} bytes from {request.client.host}"
            )
            raise HTTPException(status_code=413, detail="Request too large")

    async def _check_global_rate_limit(self, request: Request):
        """Global rate limiting per IP"""
        client_ip = request.client.host

        # Allow higher limits for authentication endpoints
        if request.url.path.startswith("/auth/"):
            return  # Handled by endpoint-specific rate limiting

        if SecurityService.is_rate_limited(client_ip, "global"):
            logger.warning(f"Global rate limit exceeded for IP: {client_ip}")
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

        for header, value in security_headers.items():
            response.headers[header] = value

    async def _log_request_metrics(
        self, request: Request, response: Response, process_time: float
    ):
        """Log request metrics for monitoring"""
        metrics = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": round(process_time, 3),
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent", "")[:100],  # Truncate
        }

        if process_time > 5.0:  # Log slow requests
            logger.warning(f"Slow request detected: {metrics}")
        elif response.status_code >= 400:
            logger.info(f"Error response: {metrics}")


class BiometricSecurityMiddleware(BaseHTTPMiddleware):
    """Specialized middleware for biometric endpoint security"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only apply to biometric authentication endpoints
        if not request.url.path.startswith("/auth/"):
            return await call_next(request)

        try:
            # Validate biometric-specific security requirements
            await self._validate_biometric_request(request)

            response = await call_next(request)

            # Add biometric-specific security headers
            self._add_biometric_headers(response)

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Biometric security middleware error: {e}")
            raise HTTPException(status_code=500, detail="Biometric security error")

    async def _validate_biometric_request(self, request: Request):
        """Validate biometric-specific security requirements"""
        # Check for WebAuthn-specific headers and requirements
        if request.method == "POST" and "verify" in request.url.path:
            # Ensure request contains proper WebAuthn structure
            # This would be expanded based on WebAuthn specification
            pass

        # Validate origin for WebAuthn requests
        origin = request.headers.get("origin")
        if origin and origin not in ["http://localhost:3000", "https://yourdomain.com"]:
            logger.warning(f"Invalid origin for biometric request: {origin}")
            raise HTTPException(status_code=400, detail="Invalid origin")

    def _add_biometric_headers(self, response: Response):
        """Add biometric-specific security headers"""
        biometric_headers = {
            "X-Biometric-Security": "enabled",
            "X-WebAuthn-Version": "2.0",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        }

        for header, value in biometric_headers.items():
            response.headers[header] = value


class AntiReplayMiddleware(BaseHTTPMiddleware):
    """Middleware to prevent replay attacks"""

    def __init__(self, app, window_seconds: int = 300):  # 5 minute window
        super().__init__(app)
        self.window_seconds = window_seconds
        self._nonce_cache = set()
        self._last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only apply to sensitive endpoints
        if request.method == "POST" and request.url.path.startswith("/auth/"):
            await self._check_replay_protection(request)

        return await call_next(request)

    async def _check_replay_protection(self, request: Request):
        """Check for replay attack indicators"""
        # Get timestamp and nonce from headers (if implemented)
        timestamp_header = request.headers.get("x-timestamp")
        nonce_header = request.headers.get("x-nonce")

        if timestamp_header and nonce_header:
            try:
                request_time = float(timestamp_header)
                current_time = time.time()

                # Check timestamp freshness
                if abs(current_time - request_time) > self.window_seconds:
                    logger.warning(f"Stale timestamp in request: {timestamp_header}")
                    raise HTTPException(
                        status_code=400, detail="Request timestamp invalid"
                    )

                # Check nonce uniqueness
                if nonce_header in self._nonce_cache:
                    logger.error(f"Replay attack detected: nonce {nonce_header}")
                    raise HTTPException(
                        status_code=400, detail="Request replay detected"
                    )

                # Add nonce to cache
                self._nonce_cache.add(nonce_header)

                # Cleanup old nonces periodically
                if current_time - self._last_cleanup > 60:  # Cleanup every minute
                    self._cleanup_nonces()
                    self._last_cleanup = current_time

            except ValueError:
                logger.warning(f"Invalid timestamp format: {timestamp_header}")
                raise HTTPException(status_code=400, detail="Invalid timestamp format")

    def _cleanup_nonces(self):
        """Clean up old nonces (simplified - use Redis with TTL in production)"""
        # In production, use Redis with automatic expiration
        # For now, clear all nonces periodically
        if len(self._nonce_cache) > 10000:  # Prevent memory bloat
            self._nonce_cache.clear()
            logger.info("Nonce cache cleared")
