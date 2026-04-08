from telebot import types
from apps.orders.models import TimeSlot
from ..core.callback_factories import agro_select_factory, slot_factory, order_confirm_factory


def sales_main_menu() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📝 Buyurtma yaratish"))
    kb.add(types.KeyboardButton("📋 Mening buyurtmalarim"))
    return kb


def time_slot_keyboard(orders=None):
    kb = types.InlineKeyboardMarkup(row_width=1)

    busy = {o.time_slot for o in orders} if orders else set()

    for i, (val, label) in enumerate(TimeSlot.choices):
        kb.add(types.InlineKeyboardButton(
            f"{'❌' if val in busy else '⏰'} {label}",
            callback_data="ignore" if val in busy else slot_factory.new(slot=str(i))
        ))

    return kb


def agronomist_list_keyboard(agronomists: list) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    for agro in agronomists:
        kb.add(types.InlineKeyboardButton(
            f"🌱 {agro.full_name}",
            callback_data=agro_select_factory.new(agro_id=agro.pk),
        ))
    return kb


def confirm_order_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton(
            "✅ Tasdiqlash",
            callback_data=order_confirm_factory.new(answer='yes'),
        ),
        types.InlineKeyboardButton(
            "✏️ Bekor qilish",
            callback_data=order_confirm_factory.new(answer='no'),
        ),
    )
    return kb


def cancel_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Bekor qilish"))
    return kb
