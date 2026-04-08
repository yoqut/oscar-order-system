from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def client_mm_inl():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "✅ Buyurtmani tasdiqlash",
            callback_data="confirm_order"
        )
    )
    return markup