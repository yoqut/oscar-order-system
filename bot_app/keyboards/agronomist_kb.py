from telebot import types
from ..core.callback_factories import (
    agro_view_factory, agro_cancel_factory, agro_complete_factory,
    agro_page_factory, root_factory, payment_factory, retreatment_factory,
)


def agronomist_main_menu() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📋 Mening buyurtmalarim"))
    kb.add(types.KeyboardButton("🔄 Faol buyurtmalar"))
    return kb


def order_actions_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton(
            "✅ Xizmat bajarildi",
            callback_data=agro_complete_factory.new(order_id=order_id),
        ),
        types.InlineKeyboardButton(
            "❌ Bekor qilish",
            callback_data=agro_cancel_factory.new(order_id=order_id),
        ),
    )
    return kb


def root_treatment_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ Ha", callback_data=root_factory.new(value='yes')),
        types.InlineKeyboardButton("❌ Yo'q", callback_data=root_factory.new(value='no')),
    )
    return kb


def payment_type_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💵 Naqd pul", callback_data=payment_factory.new(ptype='cash')),
        types.InlineKeyboardButton("💳 Karta", callback_data=payment_factory.new(ptype='card')),
        types.InlineKeyboardButton("🏦 Bank o'tkazmasi", callback_data=payment_factory.new(ptype='bank_transfer')),
    )
    return kb


def retreatment_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ Ha", callback_data=retreatment_factory.new(value='yes')),
        types.InlineKeyboardButton("❌ Yo'q", callback_data=retreatment_factory.new(value='no')),
    )
    return kb


def cancel_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Bekor qilish"))
    return kb


def orders_list_keyboard(orders: list, page: int = 0, page_size: int = 5) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    start = page * page_size
    end = start + page_size
    page_orders = orders[start:end]

    for order in page_orders:
        slot = order.get_time_slot_display()
        kb.add(types.InlineKeyboardButton(
            f"#{order.pk} — {order.client_name} ({slot})",
            callback_data=agro_view_factory.new(order_id=order.pk),
        ))

    nav_row = []
    if page > 0:
        nav_row.append(types.InlineKeyboardButton(
            "⬅️", callback_data=agro_page_factory.new(page=page - 1),
        ))
    if end < len(orders):
        nav_row.append(types.InlineKeyboardButton(
            "➡️", callback_data=agro_page_factory.new(page=page + 1),
        ))
    if nav_row:
        kb.row(*nav_row)

    return kb
