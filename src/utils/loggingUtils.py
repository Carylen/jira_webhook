# loggingUtils.py

from __future__ import annotations

import contextvars
import logging
import sys
import time
import uuid
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="untracked")

def get_request_id() -> str:
    """Get current request_id from context."""
    return request_id_ctx.get()

# Dedicated access logger (separate from app logger)
access_logger = logging.getLogger("http.access")

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    One middleware that:
    - reads or generates X-Request-ID
    - sets request_id context var
    - calls downstream handlers
    - adds X-Request-ID to response
    - logs access line with latency
    - resets context var (prevents leakage)
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)

        start = time.time()
        response = None
        try:
            response = await call_next(request)
            # Echo request id to the client
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            latency_ms = (time.time() - start) * 1000.0

            # Log access line while request_id context is still set
            access_logger.info(
                "method=%s path=%s status=%s client=%s latency=%.2fms",
                request.method,
                request.url.path,
                response.status_code if response else "NA",
                request.client.host if request.client else "unknown",
                latency_ms,
            )

            # Always reset context (important for async correctness)
            request_id_ctx.reset(token)

class RequestIDFilter(logging.Filter):
    """Attach request_id to every log record."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True

def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure logging for the entire app.

    - stdout: <= INFO
    - stderr: >= WARNING
    - request_id injected via filter
    - force=True: overrides uvicorn/gunicorn default handlers
    """

    formatter = logging.Formatter(
        "%(asctime)s | %(request_id)s | %(name)s | %(levelname)s | %(message)s"
    )

    req_id_filter = RequestIDFilter()

    # STDOUT handler (INFO and below)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(lambda r: r.levelno <= logging.INFO)
    stdout_handler.addFilter(req_id_filter)
    stdout_handler.setFormatter(formatter)

    # STDERR handler (WARNING and above)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.addFilter(req_id_filter)
    stderr_handler.setFormatter(formatter)

    logging.basicConfig(
        level=log_level.upper(),
        handlers=[stdout_handler, stderr_handler],
        force=True,  # critical for uvicorn/gunicorn
    )

    # Tune noisy loggers (optional)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    # If you want ONLY your access logger (and not uvicorn's)
    logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL)

    # Keep our dedicated access logger enabled
    logging.getLogger("http.access").setLevel(logging.INFO)

def log_endpoint(
    logger: logging.Logger,
    event: str,
    latency_ms: float,
    **kwargs,
) -> None:
    """
    Log structured event with automatic request_id (via filter) and custom fields.

    Example:
        log_endpoint(logger, "JIRA_WEBHOOK", latency_ms, issue_key="SDO-1", processed=True)
    """
    fields = {k: v for k, v in kwargs.items() if v is not None}
    fields_str = " | ".join(f"{k}={v}" for k, v in fields.items())

    if fields_str:
        logger.info("%s | latency_ms=%.2f | %s", event, latency_ms, fields_str)
    else:
        logger.info("%s | latency_ms=%.2f", event, latency_ms)
