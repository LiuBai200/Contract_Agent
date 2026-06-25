import logging

from fastapi import Depends, HTTPException, Request, status

from backend.config import settings
from backend.db.models import User
from backend.security.dependencies import get_current_user
from backend.services.redis_client import close_redis_client, get_redis_client


logger = logging.getLogger(__name__)


def rate_limit(scope: str, limit: int, window_seconds: int):
    async def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> None:
        if not settings.rate_limit_enabled:
            return

        key = f"rate:{scope}:user:{current_user.id}"
        allowed = await _check_rate_limit(key, limit, window_seconds)
        if allowed:
            return

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Try again in {window_seconds} seconds.",
            headers={"Retry-After": str(window_seconds)},
        )

    return dependency


async def close_rate_limiter() -> None:
    await close_redis_client()


async def _check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    try:
        redis = get_redis_client()
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, window_seconds)
        return current <= limit
    except Exception as exc:
        logger.warning("Redis rate limit check failed: %s", exc)
        return settings.rate_limit_fail_open
