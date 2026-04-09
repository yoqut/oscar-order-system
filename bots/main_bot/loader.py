"""
Main bot singleton (for admin, sales, agronomist).
Import `bot` and `handler` from here in all main_bot handlers.
"""
from telebot.async_telebot import AsyncTeleBot
from telebot import asyncio_filters
from telebot.states.asyncio.middleware import StateMiddleware

from config import settings
from bots.base.decorator import make_handler
from bots.base.filters import (
    RoleFilter, IsAdminFilter, IsSalesFilter,
    IsAgronomistFilter, IsClientFilter, IsStaffFilter,
    CallFilter, F,
)

from telebot.asyncio_storage import StateRedisStorage

_storage = StateRedisStorage(
    host="localhost",
    port=6379,
    db=5,
)


bot = AsyncTeleBot(
    token=settings.MAIN_BOT_TOKEN,
    parse_mode='HTML',
    state_storage=_storage,
)

bot.setup_middleware(StateMiddleware(bot))

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.add_custom_filter(asyncio_filters.IsDigitFilter())
bot.add_custom_filter(asyncio_filters.TextMatchFilter())
bot.add_custom_filter(RoleFilter())
bot.add_custom_filter(IsAdminFilter())
bot.add_custom_filter(IsSalesFilter())
bot.add_custom_filter(IsAgronomistFilter())
bot.add_custom_filter(IsClientFilter())
bot.add_custom_filter(IsStaffFilter())
bot.add_custom_filter(CallFilter())
bot.add_custom_filter(F())

handler = make_handler(bot, bot_name='main_bot')
