import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Extract request info
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        user_agent = request.headers.get("user-agent", "unknown")

        # Log request
        logger.info(
            f"Request: {method} {path}",
            additional_info={
                "ip_address": client_ip,
                "action": "http_request",
                "resource": path,
                "method": method,
                "user_agent": user_agent,
            },
        )

        # Process request
        try:
            response: Response = await call_next(request)
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"Response: {method} {path} - {response.status_code}",
                additional_info={
                    "ip_address": client_ip,
                    "action": "http_response",
                    "resource": path,
                    "status": "success" if response.status_code < 400 else "error",
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                e,
                additional_info={
                    "ip_address": client_ip,
                    "action": "http_error",
                    "resource": path,
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration * 1000, 2),
                },
                exc_info=True,
            )
            raise
