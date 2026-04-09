from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from apps.orders.models import Order, TimeSlot
from core.callbacks import (
    agro_select_factory, slot_factory, order_confirm_factory,
    sales_accept_client_order_factory, sales_assign_agro_factory, sales_assign_slot_factory,
)


def sales_main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📝 Buyurtma yaratish"))
    kb.add(KeyboardButton("📋 Client so'rovlari"), KeyboardButton("📦 Barcha buyurtmalar"))
    return kb


def cancel_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Bekor qilish"))
    return kb


def agronomist_list_keyboard(agronomists) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for agro in agronomists:
        kb.add(InlineKeyboardButton(
            f"🌱 {agro.full_name}",
            callback_data=agro_select_factory.new(agro_id=agro.pk),
        ))
    return kb


def time_slot_keyboard(busy_slots: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, (value, label) in enumerate(TimeSlot.choices):
        icon = "❌" if value in busy_slots else "✅"
        kb.add(InlineKeyboardButton(
            f"{icon} {label}",
            callback_data=slot_factory.new(slot=str(idx)),
        ))
    return kb


def confirm_order_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=order_confirm_factory.new(answer='yes')),
        InlineKeyboardButton("❌ Bekor", callback_data=order_confirm_factory.new(answer='no')),
    )
    return kb


def client_order_accept_keyboard(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(
        "✅ Qabul qilish va agronom belgilash",
        callback_data=sales_accept_client_order_factory.new(order_id=order_id),
    ))
    return kb


def assign_agro_keyboard(order_id: int, agronomists) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for agro in agronomists:
        kb.add(InlineKeyboardButton(
            f"🌱 {agro.full_name}",
            callback_data=sales_assign_agro_factory.new(order_id=order_id, agro_id=agro.pk),
        ))
    return kb


def assign_slot_keyboard(order_id: int, busy_slots: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, (value, label) in enumerate(TimeSlot.choices):
        icon = "❌" if value in busy_slots else "✅"
        kb.add(InlineKeyboardButton(
            f"{icon} {label}",
            callback_data=sales_assign_slot_factory.new(order_id=order_id, slot=str(idx)),
        ))
    return kb
