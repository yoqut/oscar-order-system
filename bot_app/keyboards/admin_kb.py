from telebot import types
from ..core.callback_factories import admin_remove_factory, admin_approve_factory, admin_cancel_order_factory


def admin_main_menu() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users"),
        types.InlineKeyboardButton("📦 Buyurtmalar", callback_data="orders"),
    )
    kb.add(
        types.InlineKeyboardButton("📢 Xabar yuborish", callback_data="notification"),
        types.InlineKeyboardButton("📊 Statistika", callback_data="stats"),
    )
    return kb


def user_management_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("➕ Sotuvchi qo'shish", callback_data="admin:add_manager"),
        types.InlineKeyboardButton("➕ Agronom qo'shish", callback_data="admin:add_agronomist"),
        types.InlineKeyboardButton("📋 Barcha sotuvchilar", callback_data="admin:list_managers"),
        types.InlineKeyboardButton("📋 Barcha agronomlar", callback_data="admin:list_agronomists"),
        types.InlineKeyboardButton("⬅️ Orqaga", callback_data="back:main_menu"),
    )
    return kb


def orders_menu_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🆕 Yangi buyurtmalar", callback_data="admin:orders_pending"),
        types.InlineKeyboardButton("✅ Tasdiqlangan", callback_data="admin:orders_approved"),
        types.InlineKeyboardButton("🔄 Bajarilmoqda", callback_data="admin:orders_inprogress"),
        types.InlineKeyboardButton("🏁 Yakunlangan", callback_data="admin:orders_completed"),
        types.InlineKeyboardButton("❌ Bekor qilingan", callback_data="admin:orders_cancelled"),
        types.InlineKeyboardButton("🔁 Qayta ishlov jadvali", callback_data="admin:orders_retreatment"),
    )
    return kb


def notifications_menu_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("👤 Foydalanuvchiga xabar", callback_data="admin:msg_user"),
        types.InlineKeyboardButton("📢 Hammaga yuborish", callback_data="admin:broadcast"),
    )
    return kb


def approve_order_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton(
            "✅ Tasdiqlash",
            callback_data=admin_approve_factory.new(order_id=order_id),
        ),
        types.InlineKeyboardButton(
            "❌ Bekor qilish",
            callback_data=admin_cancel_order_factory.new(order_id=order_id),
        ),
    )
    return kb


def user_remove_keyboard(user_pk: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🗑 O'chirish",
        callback_data=admin_remove_factory.new(user_pk=user_pk),
    ))
    return kb


def confirm_broadcast_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("✅ Yuborish", callback_data="broadcast:confirm"),
        types.InlineKeyboardButton("❌ Bekor", callback_data="broadcast:cancel"),
    )
    return kb


def back_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("⬅️ Orqaga"))
    return kb
