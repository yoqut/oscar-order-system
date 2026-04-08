from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeAlias, TypeVar

from telebot import types

from bot_app.core.loader import bot
from .sender import Sender

HandlerMessage: TypeAlias = types.Message | types.CallbackQuery
P = ParamSpec("P")
R = TypeVar("R")

DEFAULT_CALLBACK_FILTER: Callable[[types.CallbackQuery], bool] = lambda _: True
_build_sender = Sender
_message_handler = bot.message_handler
_callback_query_handler = bot.callback_query_handler

def handler(
    *,
    callback: bool = False,
    func: Callable[[Any], bool] | None = None,
    **decorator_kwargs: Any,
) -> Callable[
    [Callable[[HandlerMessage, Sender, P], Awaitable[R]]],
    Callable[[HandlerMessage, P], Awaitable[R]],
]:
    def decorator(
        handler_func: Callable[[HandlerMessage, Sender, P], Awaitable[R]],
    ) -> Callable[[HandlerMessage, P], Awaitable[R]]:
        if not inspect.iscoroutinefunction(handler_func):
            raise TypeError(
                f"{handler_func.__module__}.{handler_func.__qualname__} must be an async function"
            )
        @wraps(handler_func)
        async def wrapper(message: HandlerMessage, *args: P.args, **kwargs: P.kwargs) -> R:
            return await handler_func(
                _build_sender(bot, message),
                *args,
                **kwargs,
            )

        if callback:
            _callback_query_handler(
                func=func or DEFAULT_CALLBACK_FILTER,
                **decorator_kwargs,
            )(wrapper)
        else:
            _message_handler(
                func=func,
                **decorator_kwargs,
            )(wrapper)

        return wrapper

    return decorator