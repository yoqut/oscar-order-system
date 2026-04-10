from datetime import date
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from apps.orders.models import TimeSlot
from core.callbacks import (
    agro_select_factory, slot_factory, order_confirm_factory,
    sales_accept_client_order_factory, sales_assign_agro_factory,
    sales_assign_slot_factory, sales_date_factory,
)


def sales_main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📝 Buyurtma yaratish", callback_data="sales:create_order"),
        InlineKeyboardButton("📋 Client so'rovlari", callback_data="sales:client_requests"),
        InlineKeyboardButton("📦 Barcha buyurtmalar", callback_data="sales:my_orders"),
    )
    return kb


def cancel_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="sales:cancel"))
    return kb


def skip_phone2_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("⏭ O'tkazish", callback_data="sales:skip_phone2"),
        InlineKeyboardButton("❌ Bekor", callback_data="sales:cancel"),
    )
    return kb


def date_picker_keyboard(date_avail: list) -> InlineKeyboardMarkup:
    """date_avail: list of (date_str 'YYYY-MM-DD', is_available)"""
    kb = InlineKeyboardMarkup(row_width=5)
    buttons = []
    for date_str, available in date_avail:
        d = date.fromisoformat(date_str)
        label = d.strftime('%d.%m') + (' ✅' if available else ' ❌')
        cb = sales_date_factory.new(date=date_str) if available else "date:busy"
        buttons.append(InlineKeyboardButton(label, callback_data=cb))
    kb.add(*buttons)
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="sales:cancel"))
    return kb


def time_slot_keyboard_avail(slot_avail: list) -> InlineKeyboardMarkup:
    """slot_avail: list of (value, label, is_available)"""
    kb = InlineKeyboardMarkup(row_width=1)
    for idx, (value, label, available) in enumerate(slot_avail):
        icon = "✅" if available else "❌"
        cb = slot_factory.new(slot=str(idx)) if available else "slot:busy"
        kb.add(InlineKeyboardButton(f"{icon} {label}", callback_data=cb))
    kb.row(
        InlineKeyboardButton("⬅️ Orqaga", callback_data="sales:back_to_date"),
        InlineKeyboardButton("❌ Bekor", callback_data="sales:cancel"),
    )
    return kb


def agronomist_list_keyboard(agronomists) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for agro in agronomists:
        kb.add(InlineKeyboardButton(
            f"🌱 {agro.full_name}",
            callback_data=agro_select_factory.new(agro_id=agro.pk),
        ))
    kb.row(
        InlineKeyboardButton("⬅️ Orqaga", callback_data="sales:back_to_slot"),
        InlineKeyboardButton("❌ Bekor", callback_data="sales:cancel"),
    )
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


def assign_slot_keyboard(order_id: int, busy_slots: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for idx, (value, label) in enumerate(TimeSlot.choices):
        icon = "❌" if value in busy_slots else "✅"
        kb.add(InlineKeyboardButton(
            f"{icon} {label}",
            callback_data=sales_assign_slot_factory.new(order_id=order_id, slot=str(idx)),
        ))
    return kb
