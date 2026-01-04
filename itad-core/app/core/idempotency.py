import hashlib
from sqlalchemy import select
from app.models.idempotency_keys import IdempotencyKey
from app.core.db import async_session


async def check_idempotency(idempotency_key: str, route: str, method: str, request_body: str) -> dict | None:
    request_hash = hashlib.sha256(request_body.encode()).hexdigest()
    async with async_session() as session:
        result = await session.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.idempotency_key == idempotency_key,
                IdempotencyKey.route == route,
                IdempotencyKey.method == method,
            )
        )
        key = result.scalar_one_or_none()
        if key:
            return {
                "status_code": key.response_status,
                "body": key.response_body_json,
            }
        return None


async def store_idempotency_response(idempotency_key: str, route: str, method: str, request_body: str, status_code: int, response_body: dict):
    request_hash = hashlib.sha256(request_body.encode()).hexdigest()
    async with async_session() as session:
        key = IdempotencyKey(
            idempotency_key=idempotency_key,
            route=route,
            method=method,
            request_hash=request_hash,
            response_status=status_code,
            response_body_json=response_body,
        )
        session.add(key)
        await session.commit()