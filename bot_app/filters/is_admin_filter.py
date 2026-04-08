from telebot.asyncio_filters import SimpleCustomFilter
from apps.accounts.models import TelegramUser, UserRole

class IsAdminFilter(SimpleCustomFilter):

    key = 'is_admin'

    async def check(self, message):
        try:
            user = await TelegramUser.objects.aget(telegram_id=message.from_user.id, is_active=True)
            return user.role == UserRole.SUPER_ADMIN
        except TelegramUser.DoesNotExist:
            return False