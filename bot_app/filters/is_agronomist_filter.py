from telebot import types
from typing import Union

from telebot.asyncio_filters import SimpleCustomFilter
from apps.accounts.models import TelegramUser, UserRole


class IsAgronomistFilter(SimpleCustomFilter):
    key = 'is_agronomist'

    async def check(self, message: Union[types.Message, types.CallbackQuery]):
        try:
            user = await TelegramUser.objects.aget(telegram_id=message.from_user.id, is_active=True)
            return user.role == UserRole.AGRONOMIST
        except TelegramUser.DoesNotExist:
            return False




