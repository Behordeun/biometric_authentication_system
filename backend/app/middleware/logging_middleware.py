import time

from app.core.logging import get_logger
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Extract request info and sanitize for log injection
        client_ip = request.client.host if request.client else "unknown"
        method = request.method.replace("\n", "").replace("\r", "")
        path = request.url.path.replace("\n", "").replace("\r", "")
        user_agent = (
            request.headers.get("user-agent", "unknown")
            .replace("\n", "")
            .replace("\r", "")
        )

        # Sanitize log message to prevent log injection
        sanitized_method = method.replace("\n", "").replace("\r", "")
        sanitized_path = path.replace("\n", "").replace("\r", "")
        sanitized_user_agent = user_agent.replace("\n", "").replace("\r", "")

        # Log request
        logger.info(
            f"Request: {sanitized_method} {sanitized_path}",
            additional_info={
                "ip_address": client_ip,
                "action": "http_request",
                "resource": sanitized_path,
                "method": sanitized_method,
                "user_agent": sanitized_user_agent,
            },
        )

        # Process request
        try:
            response: Response = await call_next(request)
            duration = time.time() - start_time

            # Log response with additional context
            logger.info(
                f"Response: {method} {path} - {response.status_code}",
                additional_info={
                    "ip_address": client_ip,
                    "action": "http_response",
                    "resource": path,
                    "status": "success" if response.status_code < 400 else "error",
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "query_params": dict(request.query_params),
                    "headers": {
                        k: v
                        for k, v in request.headers.items()
                        if k.lower() not in {"authorization", "cookie"}
                    },
                    # Optionally, log response body if not too large or sensitive
                    # "response_body": await response.body() if hasattr(response, "body") else None,
                },
            )

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Exception occurred during request: {method} {path} - {str(e)}",
                additional_info={
                    "ip_address": client_ip,
                    "action": "http_error",
                    "resource": path,
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration * 1000, 2),
                    "query_params": dict(request.query_params),
                    "headers": {
                        k: v
                        for k, v in request.headers.items()
                        if k.lower() not in {"authorization", "cookie"}
                    },
                },
                exc_info=True,
            )
            raise
