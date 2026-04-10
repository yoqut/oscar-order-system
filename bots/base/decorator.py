"""
make_handler(bot, bot_name) — factory that returns a @handler decorator
bound to a specific bot instance.

The returned decorator:
  1. Looks up the user's language from Redis cache
  2. Injects Sender(bot, msg, lang) as the first argument
  3. Passes through *args, **kwargs (StateContext from StateMiddleware flows through)
  4. Never crashes the bot — all exceptions are caught and logged

Usage:
    # In loader.py:
    bot = AsyncTeleBot(token)
    handler = make_handler(bot, 'main_bot')

    # In handlers:
    @handler(commands=['start'], is_admin=True)
    async def cmd_start(sender: Sender, state: StateContext): ...

    @handler(callback=True, config=rate_factory.filter())
    async def cb_rate(sender: Sender, state: StateContext): ...
"""
from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from telebot.async_telebot import AsyncTeleBot
from telebot.types import CallbackQuery, Message

from bots.base.sender import Sender
from core.i18n import get_user_lang

logger = logging.getLogger(__name__)

_DEFAULT_CB_FILTER: Callable[[CallbackQuery], bool] = lambda _: True


def make_handler(bot: AsyncTeleBot, bot_name: str = 'bot') -> Callable[..., Callable[[Callable], Callable[..., Awaitable[None]]]]:
    """
    Returns a @handler decorator factory bound to *bot*.

    Parameters
    ----------
    bot       : AsyncTeleBot instance
    bot_name  : used for logging only
    """

    def handler(
        *,
        callback: bool = False,
        func: Callable[[Any], bool] | None = None,
        **decorator_kwargs: Any,
    ) -> Callable:
        """
        Decorator factory.

        Parameters
        ----------
        callback        : True for callback_query handlers
        func            : optional additional filter predicate
        decorator_kwargs: passed directly to bot.message_handler / bot.callback_query_handler
        """

        def decorator(handler_func: Callable) -> Callable:
            if not inspect.iscoroutinefunction(handler_func):
                raise TypeError(
                    f"{handler_func.__module__}.{handler_func.__qualname__} must be async"
                )

            @wraps(handler_func)
            async def wrapper(msg: Message | CallbackQuery, *args: Any, **kwargs: Any) -> None:
                try:
                    user = msg.from_user
                    lang = await get_user_lang(user.id) if user else 'uz'
                    sender = Sender(bot, msg, lang)
                    await handler_func(sender, *args, **kwargs)
                except Exception:
                    logger.exception(
                        "[%s] Unhandled error in handler %s",
                        bot_name,
                        handler_func.__qualname__,
                    )

            if callback:
                bot.callback_query_handler(
                    func=func or _DEFAULT_CB_FILTER,
                    **decorator_kwargs,
                )(wrapper)
            else:
                bot.message_handler(
                    func=func,
                    **decorator_kwargs,
                )(wrapper)

            return wrapper

        return decorator

    return handler
