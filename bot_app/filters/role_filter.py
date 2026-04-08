"""
Role-based filter for Telegram bot_app handlers.

Usage:
    @bot_app.message_handler(role=["admin", "sales_manager"])
    async def handler(message): ...

    @bot_app.callback_query_handler(func=None, role=["agronomist"])
    async def handler(call): ...

Supported role aliases (maps to UserRole values):
    "admin"         → super_admin
    "sales_manager" → sales_manager
    "agronomist"    → agronomist
    "client"        → client
    "staff"         → super_admin + sales_manager + agronomist
"""
from telebot.asyncio_filters import AdvancedCustomFilter
from apps.accounts.models import TelegramUser, UserRole

_ALIASES: dict[str, list[str]] = {
    "admin":         [UserRole.SUPER_ADMIN],
    "sales_manager": [UserRole.SALES_MANAGER],
    "agronomist":    [UserRole.AGRONOMIST],
    "client":        [UserRole.CLIENT],
    "staff":         [UserRole.SUPER_ADMIN, UserRole.SALES_MANAGER, UserRole.AGRONOMIST],
    # Allow bare role values too
    UserRole.SUPER_ADMIN:    [UserRole.SUPER_ADMIN],
    UserRole.SALES_MANAGER:  [UserRole.SALES_MANAGER],
    UserRole.AGRONOMIST:     [UserRole.AGRONOMIST],
    UserRole.CLIENT:         [UserRole.CLIENT],
}


class RoleFilter(AdvancedCustomFilter):
    """
    key='role' — accepts a single role string or a list of role strings.
    The update is allowed through only if the sender's DB role is in the set.
    Inactive users are always blocked.
    """
    key = "role"

    async def check(self, update, allowed_roles) -> bool:
        # Normalise to list
        if isinstance(allowed_roles, str):
            allowed_roles = [allowed_roles]

        # Build flat set of DB role values
        role_set: set[str] = set()
        for alias in allowed_roles:
            role_set.update(_ALIASES.get(alias, [alias]))

        user_id = self._get_user_id(update)
        if user_id is None:
            return False

        try:
            user = await TelegramUser.objects.aget(telegram_id=user_id, is_active=True)
            return user.role in role_set
        except TelegramUser.DoesNotExist:
            return False

    @staticmethod
    def _get_user_id(update) -> int | None:
        if hasattr(update, "from_user") and update.from_user:
            return update.from_user.id
        return None
