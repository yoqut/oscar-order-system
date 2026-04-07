"""
Bot singleton — import `bot` from here everywhere.

Django setup is intentionally NOT called here to avoid double-setup issues.
Django is already configured when the WSGI/ASGI application loads, so handlers
that need ORM access simply import models directly.
"""


from telebot.asyncio_storage import StateMemoryStorage
from telebot.states.asyncio.context import StateContext
from telebot.async_telebot import AsyncTeleBot
from config import settings 

state_storage = StateMemoryStorage()  # don't use this in production; switch to redis

bot = AsyncTeleBot(
    token=settings.BOT_TOKEN,
    parse_mode='HTML',
    state_storage=state_storage
)

from telebot.states.asyncio.middleware import StateMiddleware

bot.setup_middleware(StateMiddleware(bot))
