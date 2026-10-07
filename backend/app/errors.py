"""API error type and JSON error handlers.

Every error response has the same shape::

    {"error": "<machine_code>", "message": "<human readable explanation>"}
"""

from __future__ import annotations

import re

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from app import config


class ApiError(Exception):
    """An expected, client-facing error with an HTTP status and machine code."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _error_response(status: int, code: str, message: str) -> tuple[Response, int]:
    """Build the standard JSON error body."""
    return jsonify({"error": code, "message": message}), status


def _snake_case(name: str) -> str:
    """Turn an HTTP reason phrase such as 'Not Found' into 'not_found'."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def register_error_handlers(app: Flask) -> None:
    """Render ApiError, HTTP errors and unexpected exceptions as JSON."""

    @app.errorhandler(ApiError)
    def handle_api_error(exc: ApiError):
        """Expected client errors raised by routes."""
        return _error_response(exc.status, exc.code, exc.message)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_exc: RequestEntityTooLarge):
        """Request body over MAX_CONTENT_LENGTH."""
        limit_mb = config.MAX_FILE_SIZE_BYTES // (1024 * 1024)
        return _error_response(413, "file_too_large", f"Files must be {limit_mb} MB or smaller.")

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        """Any other HTTP error (404, 405...)."""
        return _error_response(exc.code or 500, _snake_case(exc.name), exc.description or exc.name)

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        """Unhandled exceptions: log details, return a generic 500."""
        app.logger.exception("Unhandled error: %s", exc)
        return _error_response(500, "internal_error", "An unexpected error occurred.")
