"""
Redis-backed state storage for pyTelegramBotAPI.

Each bot uses its own prefix so states don't bleed between bots:
  main_bot  → "main:state:{chat_id}:{user_id}:*"
  client_bot → "client:state:{chat_id}:{user_id}:*"

TTL: 24 hours (resets on every write).
"""
import json
from telebot.asyncio_storage.base_storage import StateStorageBase

from core.redis_client import redis

STATE_TTL = 60 * 60 * 24  # 24 hours


class RedisStateStorage(StateStorageBase):

    def __init__(self, prefix: str = 'bot'):
        self.prefix = prefix

    def _state_key(self, chat_id, user_id) -> str:
        return f"{self.prefix}:state:{chat_id}:{user_id}"

    def _data_key(self, chat_id, user_id) -> str:
        return f"{self.prefix}:data:{chat_id}:{user_id}"

    async def set_state(self, chat_id, user_id, state, *args, **kwargs):
        key = self._state_key(chat_id, user_id)
        await redis.set(key, str(state), ex=STATE_TTL)

    async def get_state(self, chat_id, user_id, *args, **kwargs):
        key = self._state_key(chat_id, user_id)
        return await redis.get(key)

    async def delete_state(self, chat_id, user_id, *args, **kwargs):
        await redis.delete(
            self._state_key(chat_id, user_id),
            self._data_key(chat_id, user_id),
        )

    async def set_data(self, chat_id, user_id, key, value, *args, **kwargs):
        redis_key = self._data_key(chat_id, user_id)
        raw = await redis.get(redis_key)
        data = json.loads(raw) if raw else {}
        data[key] = value
        await redis.set(redis_key, json.dumps(data, ensure_ascii=False), ex=STATE_TTL)

    async def get_data(self, chat_id, user_id, *args, **kwargs):
        key = self._data_key(chat_id, user_id)
        raw = await redis.get(key)
        return json.loads(raw) if raw else {}

    async def reset_data(self, chat_id, user_id, *args, **kwargs):
        await redis.delete(self._data_key(chat_id, user_id))

    async def update_data(self, chat_id, user_id, data: dict, *args, **kwargs):
        redis_key = self._data_key(chat_id, user_id)
        raw = await redis.get(redis_key)
        current = json.loads(raw) if raw else {}
        current.update(data)
        await redis.set(redis_key, json.dumps(current, ensure_ascii=False), ex=STATE_TTL)
