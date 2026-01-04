import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        correlation_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        response = await call_next(request)

        response.headers["X-Request-Id"] = request_id
        response.headers["X-Correlation-Id"] = correlation_id

        return response