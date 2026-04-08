"""
Unified catch-all text message router.

Must be imported LAST in bot_app/handlers/__init__.py so that state-specific
handlers (sales, agronomist) — which use pyTelegramBotAPI's in-memory
StateContext — are registered first and fire before this catch-all.

Admin and client text set_states both use StateManager (DB-backed) so they
are handled here regardless of pyTelegramBotAPI's in-memory state.
"""
import logging
from telebot import types

from ..core.loader import bot
from ..utils.state_manager import StateManager
from apps.accounts.models import TelegramUser, UserRole

logger = logging.getLogger(__name__)


@bot.message_handler(func=lambda m: True, content_types=['text'])
async def unified_text_router(message: types.Message) -> None:
    try:
        user = await TelegramUser.objects.aget(telegram_id=message.from_user.id)
    except TelegramUser.DoesNotExist:
        return

    state, data = await StateManager.get_state_and_data(message.from_user.id)
    if not state:
        return

    if user.role == UserRole.SUPER_ADMIN and "AdminStates:" in str(state):
        from handlers.admins.callbacks import handle_admin_text
        await handle_admin_text(message, state, data)

    elif user.role == UserRole.CLIENT and "ClientStates:" in str(state):
        from bot_app.handlers.client import handle_client_text
        await handle_client_text(message, state, data)
