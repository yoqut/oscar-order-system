from telebot import types
from apps.orders.models import TimeSlot


def sales_main_menu() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📝 Buyurtma yaratish"))
    kb.add(types.KeyboardButton("📋 Mening buyurtmalarim"))
    return kb


def time_slot_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    for value, label in TimeSlot.choices:
        kb.add(types.InlineKeyboardButton(f"⏰ {label}", callback_data=f"slot:{value}"))
    return kb


def agronomist_list_keyboard(agronomists: list) -> types.InlineKeyboardMarkup:
    """Build an inline keyboard from a list of TelegramUser (agronomists)."""
    kb = types.InlineKeyboardMarkup(row_width=1)
    for agro in agronomists:
        kb.add(types.InlineKeyboardButton(
            f"🌱 {agro.full_name}",
            callback_data=f"agro_select:{agro.pk}"
        ))
    return kb


def confirm_order_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ Tasdiqlash", callback_data="order_confirm:yes"),
        types.InlineKeyboardButton("✏️ Bekor qilish", callback_data="order_confirm:no"),
    )
    return kb


def cancel_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Bekor qilish"))
    return kb
