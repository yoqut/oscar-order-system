"""
Bot singleton — import `bot_app` from here everywhere.

Django setup is intentionally NOT called here to avoid double-setup issues.
Django is already configured when the WSGI/ASGI application loads, so handlers
that need ORM access simply import models directly.
"""
from telebot.asyncio_storage import StateMemoryStorage
from telebot.async_telebot import AsyncTeleBot
from telebot import asyncio_filters

from config import settings

state_storage = StateMemoryStorage()

bot = AsyncTeleBot(
    token=settings.BOT_TOKEN,
    parse_mode='HTML',
    state_storage=state_storage,
)

# ── Built-in pyTelegramBotAPI middleware ──────────────────────────────────────
from telebot.states.asyncio.middleware import StateMiddleware
bot.setup_middleware(StateMiddleware(bot))

# ── Built-in filters ──────────────────────────────────────────────────────────
bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.add_custom_filter(asyncio_filters.IsDigitFilter())
bot.add_custom_filter(asyncio_filters.TextMatchFilter())


from ..filters.role_filter import RoleFilter
from ..filters.callback_filter import CallFilter, F
from ..filters.is_admin_filter import IsAdminFilter
from ..filters.is_client_filter import IsClientFilter
from ..filters.is_agronomist_filter import IsAgronomistFilter
from ..filters.is_sales_filter import IsSalesFilter


bot.add_custom_filter(RoleFilter())
bot.add_custom_filter(IsAdminFilter())
bot.add_custom_filter(IsClientFilter())
bot.add_custom_filter(IsAgronomistFilter())
bot.add_custom_filter(IsSalesFilter())
bot.add_custom_filter(CallFilter())
bot.add_custom_filter(F())