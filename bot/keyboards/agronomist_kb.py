from telebot import types


def agronomist_main_menu() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📋 Mening buyurtmalarim"))
    kb.add(types.KeyboardButton("🔄 Faol buyurtmalar"))
    return kb


def order_actions_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ Xizmat bajarildi", callback_data=f"agro:complete:{order_id}"),
        types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"agro:cancel:{order_id}"),
    )
    return kb


def root_treatment_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ Ha", callback_data="root:yes"),
        types.InlineKeyboardButton("❌ Yo'q", callback_data="root:no"),
    )
    return kb


def payment_type_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("💵 Naqd pul", callback_data="payment:cash"),
        types.InlineKeyboardButton("💳 Karta", callback_data="payment:card"),
        types.InlineKeyboardButton("🏦 Bank o'tkazmasi", callback_data="payment:bank_transfer"),
    )
    return kb


def retreatment_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ Ha", callback_data="retreatment:yes"),
        types.InlineKeyboardButton("❌ Yo'q", callback_data="retreatment:no"),
    )
    return kb


def cancel_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Bekor qilish"))
    return kb


def orders_list_keyboard(orders: list, page: int = 0, page_size: int = 5) -> types.InlineKeyboardMarkup:
    """Paginated inline keyboard for order list."""
    kb = types.InlineKeyboardMarkup(row_width=1)
    start = page * page_size
    end = start + page_size
    page_orders = orders[start:end]

    for order in page_orders:
        slot = order.get_time_slot_display()
        kb.add(types.InlineKeyboardButton(
            f"#{order.pk} — {order.client_name} ({slot})",
            callback_data=f"agro:view:{order.pk}"
        ))

    nav_row = []
    if page > 0:
        nav_row.append(types.InlineKeyboardButton("⬅️", callback_data=f"agro:page:{page - 1}"))
    if end < len(orders):
        nav_row.append(types.InlineKeyboardButton("➡️", callback_data=f"agro:page:{page + 1}"))
    if nav_row:
        kb.row(*nav_row)

    return kb
