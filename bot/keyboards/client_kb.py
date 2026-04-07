from telebot import types


def client_order_notification_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    """Keyboard sent when order is first created — accept or cancel."""
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ Qabul qilaman", callback_data=f"client:accept:{order_id}"),
        types.InlineKeyboardButton("❌ Bekor qilaman", callback_data=f"client:cancel:{order_id}"),
    )
    return kb


def client_service_done_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    """Keyboard sent when agronomist marks service as completed."""
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"client:confirm:{order_id}"),
        types.InlineKeyboardButton("❌ Rad etish", callback_data=f"client:reject:{order_id}"),
    )
    return kb


def rating_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=5)
    kb.add(*[
        types.InlineKeyboardButton(f"{i}⭐", callback_data=f"rate:{order_id}:{i}")
        for i in range(1, 6)
    ])
    return kb


def skip_comment_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="comment:skip"))
    return kb
