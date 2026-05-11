"""Upstash Redis через REST API – работает в serverless без TCP-соединений."""

from upstash_redis.asyncio import Redis

from bot.config import settings


redis = Redis(
    url=settings.upstash_redis_rest_url,
    token=settings.upstash_redis_rest_token,
)


async def rate_limit_check(user_id: int, limit: int = 20, window: int = 60) -> bool:
    """Возвращает True если можно продолжать, False если лимит превышен."""
    key = f'rl:{user_id}'
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window)
    return current <= limit
