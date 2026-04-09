"""
Client bot singleton.
Import `bot` and `handler` from here in all client_bot handlers.
"""
from telebot.async_telebot import AsyncTeleBot
from telebot import asyncio_filters
from telebot.states.asyncio.middleware import StateMiddleware

from config import settings
from bots.base.decorator import make_handler
from bots.base.filters import (
    IsClientFilter, CallFilter, F,
)
from telebot.asyncio_storage import StateRedisStorage

_storage = StateRedisStorage(
    host="localhost",
    port=6379,
    db=5,
)

bot = AsyncTeleBot(
    token=settings.CLIENT_BOT_TOKEN,
    parse_mode='HTML',
    state_storage=_storage,
)

bot.setup_middleware(StateMiddleware(bot))

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.add_custom_filter(asyncio_filters.IsDigitFilter())
bot.add_custom_filter(asyncio_filters.TextMatchFilter())
bot.add_custom_filter(IsClientFilter())
bot.add_custom_filter(CallFilter())
bot.add_custom_filter(F())

handler = make_handler(bot, bot_name='client_bot')
