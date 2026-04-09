from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from core.callbacks import (
    agro_view_factory, agro_cancel_factory, agro_complete_factory,
    agro_page_factory, root_factory, payment_factory, retreatment_factory,
)

PAGE_SIZE = 5


def agronomist_main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📋 Mening buyurtmalarim"))
    return kb


def cancel_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Bekor qilish"))
    return kb


def orders_list_keyboard(orders, page: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    start = page * PAGE_SIZE
    page_orders = orders[start:start + PAGE_SIZE]

    for order in page_orders:
        kb.add(InlineKeyboardButton(
            f"#{order.pk} — {order.client_name}",
            callback_data=agro_view_factory.new(order_id=order.pk),
        ))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=agro_page_factory.new(page=page - 1)))
    if start + PAGE_SIZE < len(orders):
        nav.append(InlineKeyboardButton("➡️", callback_data=agro_page_factory.new(page=page + 1)))
    if nav:
        kb.row(*nav)
    return kb


def order_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Bajarildi", callback_data=agro_complete_factory.new(order_id=order_id)),
        InlineKeyboardButton("❌ Bekor", callback_data=agro_cancel_factory.new(order_id=order_id)),
    )
    return kb


def root_treatment_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Ha", callback_data=root_factory.new(value='true')),
        InlineKeyboardButton("❌ Yo'q", callback_data=root_factory.new(value='false')),
    )
    return kb


def payment_type_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💵 Naqd pul", callback_data=payment_factory.new(ptype='cash')),
        InlineKeyboardButton("💳 Karta", callback_data=payment_factory.new(ptype='card')),
        InlineKeyboardButton("🏦 Bank o'tkazmasi", callback_data=payment_factory.new(ptype='bank_transfer')),
    )
    return kb


def retreatment_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Ha", callback_data=retreatment_factory.new(value='true')),
        InlineKeyboardButton("❌ Yo'q", callback_data=retreatment_factory.new(value='false')),
    )
    return kb
