from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.callbacks import (
    agro_view_factory, agro_cancel_factory, agro_complete_factory,
    agro_page_factory, root_factory, payment_factory, retreatment_factory,
)

PAGE_SIZE = 5


def agronomist_main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📋 Mening buyurtmalarim", callback_data="agro:my_orders"))
    return kb


def cancel_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="agro:cancel"))
    return kb


def orders_list_keyboard(orders, page: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    start = page * PAGE_SIZE
    page_orders = orders[start:start + PAGE_SIZE]

    for order in page_orders:
        date_str = order.visit_date.strftime('%d.%m') if order.visit_date else '—'
        kb.add(InlineKeyboardButton(
            f"#{order.pk} — {order.client_name} | {date_str}",
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
