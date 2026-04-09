"""
Shared async Redis client.
Import `redis` from here everywhere instead of creating new connections.
"""
import redis.asyncio as aioredis
from django.conf import settings

redis: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    encoding='utf-8',
    decode_responses=True,
)
