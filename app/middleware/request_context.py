import time
import uuid

from fastapi import Request
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.audit_context import reset_request_metadata, set_request_metadata
from app.core.constants import HEADER_PROCESS_TIME, HEADER_REQUEST_ID
from app.core.logging import request_id_var


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(HEADER_REQUEST_ID) or str(uuid.uuid4())
        request.state.request_id = request_id

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("request_id", request_id)

        token = request_id_var.set(request_id)
        metadata_token = set_request_metadata(
            url=request.url.path,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=request_id,
        )
        try:
            start = time.perf_counter()
            response = await call_next(request)
            process_time = time.perf_counter() - start
            response.headers[HEADER_REQUEST_ID] = request_id
            response.headers[HEADER_PROCESS_TIME] = f"{process_time:.4f}s"
            return response
        finally:
            request_id_var.reset(token)
            reset_request_metadata(metadata_token)
