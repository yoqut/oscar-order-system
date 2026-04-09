"""
Distributed lock manager using Redis SETNX.
Prevents double-click / race conditions on callback handlers.

Usage:
    async with acquire_lock(f"order_confirm:{user_id}"):
        # only one execution at a time
        ...

    # Or manual:
    if not await try_lock(key):
        await bot.answer_callback_query(call.id, "⏳ Iltimos kuting...")
        return
    try:
        ...
    finally:
        await release_lock(key)
"""
import asyncio
from contextlib import asynccontextmanager

from core.redis_client import redis

DEFAULT_TTL = 5  # seconds


async def try_lock(key: str, ttl: int = DEFAULT_TTL) -> bool:
    """
    Attempt to acquire a lock. Returns True if acquired, False if already held.
    """
    result = await redis.set(f"lock:{key}", '1', ex=ttl, nx=True)
    return result is True


async def release_lock(key: str) -> None:
    await redis.delete(f"lock:{key}")


@asynccontextmanager
async def acquire_lock(key: str, ttl: int = DEFAULT_TTL):
    """
    Async context manager that waits until lock is acquired.
    Raises asyncio.TimeoutError if lock is not acquired within ttl seconds.
    """
    deadline = asyncio.get_event_loop().time() + ttl
    while True:
        if await try_lock(key, ttl):
            try:
                yield
            finally:
                await release_lock(key)
            return
        if asyncio.get_event_loop().time() > deadline:
            raise asyncio.TimeoutError(f"Could not acquire lock: {key}")
        await asyncio.sleep(0.1)
