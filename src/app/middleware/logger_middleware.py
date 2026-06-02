# app/middleware/request_id.py
import uuid

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

log = structlog.get_logger()

class LoggerMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to the context variables.

    Parameters
    ----------
    app: FastAPI
        The FastAPI application instance.
    """

    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Add request ID to the context variables.
        """
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()

        # Read request body
        req_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                req_body = body_bytes.decode("utf-8")
            except Exception:
                pass

            # Repopulate stream so the actual route can read it again
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            client_host=request.client.host if request.client else None,
            status_code=None,
            path=request.url.path,
            method=request.method,
            request_body=req_body,
        )

        log.info(f"Incoming Request: {request.method} {request.url.path}")

        response = await call_next(request)

        # We can't directly read streaming response body easily without consuming it.
        # Capturing response body is usually complex. We log status instead.

        structlog.contextvars.bind_contextvars(status_code=response.status_code)

        log.info(f"Outgoing Response: {response.status_code} for {request.method} {request.url.path}")

        response.headers["X-Request-ID"] = request_id
        return response
