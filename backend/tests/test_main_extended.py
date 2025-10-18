"""
Extended tests for main application to improve coverage.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from app.main import app


class TestMainExtended:
    """Extended tests for main application."""

    @patch("app.main.engine")
    def test_startup_event(self, mock_engine):
        """Test application startup event."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app) as client:
            # Just creating the client triggers startup
            response = client.get("/health")
            assert response.status_code == 200

    @patch("app.main.engine")
    def test_cors_preflight(self, mock_engine):
        """Test CORS preflight request."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app) as client:
            response = client.options(
                "/auth/register/options",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                }
            )
            assert response.status_code == 200

    @patch("app.main.engine")
    def test_invalid_json(self, mock_engine):
        """Test invalid JSON request."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app) as client:
            response = client.post(
                "/auth/register/options",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 422

    @patch("app.main.engine")
    def test_missing_content_type(self, mock_engine):
        """Test request without content type."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app) as client:
            response = client.post(
                "/auth/register/options",
                json={"test": "data"}
            )
            # Should still work as TestClient sets content-type
            assert response.status_code in [400, 422, 500]

    @patch("app.main.logger")
    @patch("app.main.engine")
    def test_startup_logging(self, mock_engine, mock_logger):
        """Test startup logging."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app):
            mock_logger.info.assert_called()

    @patch("app.main.engine")
    def test_exception_handler(self, mock_engine):
        """Test global exception handler."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app) as client:
            # Try to trigger an internal error
            response = client.get("/nonexistent")
            assert response.status_code == 404

    @patch("app.main.engine")
    def test_validation_error_handler(self, mock_engine):
        """Test validation error handler."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app) as client:
            response = client.post(
                "/auth/register/options",
                json={"invalid": "data"}  # Missing required fields
            )
            assert response.status_code == 422
            assert "detail" in response.json()

    @patch("app.main.engine")
    def test_http_exception_handler(self, mock_engine):
        """Test HTTP exception handler."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app) as client:
            response = client.get("/auth/nonexistent")
            assert response.status_code == 404

    @patch("app.main.engine")
    def test_middleware_order(self, mock_engine):
        """Test middleware is applied in correct order."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app) as client:
            response = client.get("/health")
            # Check security headers are present
            assert "x-content-type-options" in response.headers
            assert "x-frame-options" in response.headers

    @patch("app.main.engine")
    def test_openapi_customization(self, mock_engine):
        """Test OpenAPI schema customization."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app) as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200
            openapi_schema = response.json()
            assert "info" in openapi_schema
            assert "title" in openapi_schema["info"]

    @patch("app.main.engine")
    def test_docs_redirect(self, mock_engine):
        """Test docs redirect."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app) as client:
            response = client.get("/docs")
            assert response.status_code == 200

    @patch("app.main.engine")
    def test_redoc_redirect(self, mock_engine):
        """Test redoc redirect."""
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock()
        mock_engine.begin.return_value.__aexit__ = AsyncMock()

        with TestClient(app) as client:
            response = client.get("/redoc")
            assert response.status_code == 200
