from telebot import types
from typing import Union

from telebot.asyncio_filters import SimpleCustomFilter
from apps.accounts.models import TelegramUser, UserRole


class IsClientFilter(SimpleCustomFilter):
    key = 'is_client'

    async def check(self, message: Union[types.Message, types.CallbackQuery]):
        try:
            user = await TelegramUser.objects.aget(telegram_id=message.from_user.id, is_active=True)
            return user.role == UserRole.CLIENT
        except TelegramUser.DoesNotExist:
            return False




