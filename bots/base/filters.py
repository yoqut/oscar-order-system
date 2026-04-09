"""
Custom filters shared by both bots.

Usage (in loader.py):
    bot.add_custom_filter(RoleFilter())
    bot.add_custom_filter(IsAdminFilter())
    ...
    bot.add_custom_filter(CallFilter())
    bot.add_custom_filter(F())
"""
from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.callback_data import CallbackDataFilter
from apps.accounts.models import TelegramUser, UserRole

_ROLE_ALIASES: dict[str, list[str]] = {
    'admin':         [UserRole.SUPER_ADMIN],
    'sales_manager': [UserRole.SALES_MANAGER],
    'agronomist':    [UserRole.AGRONOMIST],
    'client':        [UserRole.CLIENT],
    'staff':         [UserRole.SUPER_ADMIN, UserRole.SALES_MANAGER, UserRole.AGRONOMIST],
    UserRole.SUPER_ADMIN:   [UserRole.SUPER_ADMIN],
    UserRole.SALES_MANAGER: [UserRole.SALES_MANAGER],
    UserRole.AGRONOMIST:    [UserRole.AGRONOMIST],
    UserRole.CLIENT:        [UserRole.CLIENT],
}


def _get_user_id(update) -> int | None:
    if hasattr(update, 'from_user') and update.from_user:
        return update.from_user.id
    return None


class RoleFilter(AdvancedCustomFilter):
    """key='role' — accepts a role string or list of role strings."""
    key = 'role'

    async def check(self, update, allowed_roles) -> bool:
        if isinstance(allowed_roles, str):
            allowed_roles = [allowed_roles]

        role_set: set[str] = set()
        for alias in allowed_roles:
            role_set.update(_ROLE_ALIASES.get(alias, [alias]))

        user_id = _get_user_id(update)
        if user_id is None:
            return False

        try:
            user = await TelegramUser.objects.aget(telegram_id=user_id, is_active=True)
            return user.role in role_set
        except TelegramUser.DoesNotExist:
            return False


class IsAdminFilter(AdvancedCustomFilter):
    key = 'is_admin'

    async def check(self, update, value: bool) -> bool:
        if not value:
            return True
        user_id = _get_user_id(update)
        if not user_id:
            return False
        try:
            user = await TelegramUser.objects.aget(telegram_id=user_id, is_active=True)
            return user.role == UserRole.SUPER_ADMIN
        except TelegramUser.DoesNotExist:
            return False


class IsSalesFilter(AdvancedCustomFilter):
    key = 'is_sales'

    async def check(self, update, value: bool) -> bool:
        if not value:
            return True
        user_id = _get_user_id(update)
        if not user_id:
            return False
        try:
            user = await TelegramUser.objects.aget(telegram_id=user_id, is_active=True)
            return user.role in (UserRole.SUPER_ADMIN, UserRole.SALES_MANAGER)
        except TelegramUser.DoesNotExist:
            return False


class IsAgronomistFilter(AdvancedCustomFilter):
    key = 'is_agronomist'

    async def check(self, update, value: bool) -> bool:
        if not value:
            return True
        user_id = _get_user_id(update)
        if not user_id:
            return False
        try:
            user = await TelegramUser.objects.aget(telegram_id=user_id, is_active=True)
            return user.role == UserRole.AGRONOMIST
        except TelegramUser.DoesNotExist:
            return False


class IsClientFilter(AdvancedCustomFilter):
    key = 'is_client'

    async def check(self, update, value: bool) -> bool:
        if not value:
            return True
        user_id = _get_user_id(update)
        if not user_id:
            return False
        try:
            user = await TelegramUser.objects.aget(telegram_id=user_id, is_active=True)
            return user.role == UserRole.CLIENT
        except TelegramUser.DoesNotExist:
            return False


class IsStaffFilter(AdvancedCustomFilter):
    """Matches admin + sales + agronomist."""
    key = 'is_staff'

    async def check(self, update, value: bool) -> bool:
        if not value:
            return True
        user_id = _get_user_id(update)
        if not user_id:
            return False
        try:
            user = await TelegramUser.objects.aget(telegram_id=user_id, is_active=True)
            return user.role in (UserRole.SUPER_ADMIN, UserRole.SALES_MANAGER, UserRole.AGRONOMIST)
        except TelegramUser.DoesNotExist:
            return False


class CallFilter(AdvancedCustomFilter):
    """key='call' — exact callback_data string match."""
    key = 'call'

    async def check(self, message, call: str) -> bool:
        return message.data == call


class F(AdvancedCustomFilter):
    """key='config' — universal filter for CallbackData factories."""
    key = 'config'

    async def check(self, call, config: CallbackDataFilter) -> bool:
        return config.check(query=call)
