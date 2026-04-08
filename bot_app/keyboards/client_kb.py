from telebot import types
from ..core.callback_factories import (
    client_accept_factory, client_cancel_factory,
    client_confirm_factory, client_reject_factory,
    rate_factory,
)


def client_order_notification_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton(
            "✅ Qabul qilaman",
            callback_data=client_accept_factory.new(order_id=order_id),
        ),
        types.InlineKeyboardButton(
            "❌ Bekor qilaman",
            callback_data=client_cancel_factory.new(order_id=order_id),
        ),
    )
    return kb


def client_service_done_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton(
            "✅ Tasdiqlash",
            callback_data=client_confirm_factory.new(order_id=order_id),
        ),
        types.InlineKeyboardButton(
            "❌ Rad etish",
            callback_data=client_reject_factory.new(order_id=order_id),
        ),
    )
    return kb


def rating_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=5)
    kb.add(*[
        types.InlineKeyboardButton(
            f"{i}⭐",
            callback_data=rate_factory.new(order_id=order_id, rating=i),
        )
        for i in range(1, 6)
    ])
    return kb


def skip_comment_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="comment:skip"))
    return kb
