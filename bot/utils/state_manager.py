"""
Database-backed FSM state manager.
Uses apps.accounts.UserState model so state survives bot restarts.
"""
import logging
from typing import Optional
from apps.accounts.models import UserState

logger = logging.getLogger(__name__)


class StateManager:

    @staticmethod
    async def get_state(telegram_id: int) -> Optional[str]:
        try:
            obj = await UserState.objects.aget(telegram_id=telegram_id)
            return obj.state
        except UserState.DoesNotExist:
            return None

    @staticmethod
    async def set_state(telegram_id: int, state: str, data: Optional[dict] = None):
        await UserState.objects.aupdate_or_create(
            telegram_id=telegram_id,
            defaults={'state': state, 'data': data if data is not None else {}},
        )

    @staticmethod
    async def get_data(telegram_id: int) -> dict:
        try:
            obj = await UserState.objects.aget(telegram_id=telegram_id)
            return obj.data or {}
        except UserState.DoesNotExist:
            return {}

    @staticmethod
    async def update_data(telegram_id: int, **kwargs):
        obj, _ = await UserState.objects.aget_or_create(telegram_id=telegram_id)
        current = obj.data or {}
        current.update(kwargs)
        obj.data = current
        await obj.asave(update_fields=['data', 'updated_at'])

    @staticmethod
    async def clear(telegram_id: int):
        await UserState.objects.filter(telegram_id=telegram_id).aupdate(state=None, data={})

    @staticmethod
    async def get_state_and_data(telegram_id: int) -> tuple[Optional[str], dict]:
        try:
            obj = await UserState.objects.aget(telegram_id=telegram_id)
            return obj.state, (obj.data or {})
        except UserState.DoesNotExist:
            return None, {}
