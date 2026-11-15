"""Request-level middleware: logging, timing, request ids and clean JSON on unexpected errors."""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("campusbite.requests")


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001 - never leak a stack trace to the client
            logger.exception("%s %s -> unhandled error [%s]", request.method, request.url.path, request_id)
            response = JSONResponse({"detail": "Internal server error"}, status_code=500)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.1f}"
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%.1f ms) [%s]", request.method, request.url.path, response.status_code, elapsed_ms, request_id
        )
        return response
