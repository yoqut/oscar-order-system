from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.callbacks import (
    admin_remove_factory, admin_approve_factory,
    admin_cancel_order_factory, admin_view_order_factory,
)


def admin_main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin:users"),
        InlineKeyboardButton("📦 Buyurtmalar", callback_data="admin:orders"),
        InlineKeyboardButton("📢 Xabar yuborish", callback_data="admin:notify"),
        InlineKeyboardButton("📊 Statistika", callback_data="admin:stats"),
    )
    return kb


def user_management_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Sotuvchi qo'sh", callback_data="admin:add_manager"),
        InlineKeyboardButton("➕ Agronom qo'sh", callback_data="admin:add_agronomist"),
        InlineKeyboardButton("👥 Sotuvchilar", callback_data="admin:list_managers"),
        InlineKeyboardButton("🌱 Agronomlar", callback_data="admin:list_agronomists"),
        InlineKeyboardButton("⬅️ Orqaga", callback_data="admin:back_main"),
    )
    return kb


def orders_menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🆕 Client so'rovlari", callback_data="admin:orders_awaiting_sales"),
        InlineKeyboardButton("⏳ Tasdiqlash kutilmoqda", callback_data="admin:orders_pending"),
        InlineKeyboardButton("✅ Tasdiqlangan", callback_data="admin:orders_approved"),
        InlineKeyboardButton("🔄 Jarayonda", callback_data="admin:orders_inprogress"),
        InlineKeyboardButton("✅ Bajarilgan", callback_data="admin:orders_completed"),
        InlineKeyboardButton("❌ Bekor qilingan", callback_data="admin:orders_cancelled"),
        InlineKeyboardButton("🔁 Qayta ishlov", callback_data="admin:orders_retreatment"),
        InlineKeyboardButton("⬅️ Orqaga", callback_data="admin:back_main"),
    )
    return kb


def notify_menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📩 Bitta foydalanuvchiga", callback_data="admin:msg_user"),
        InlineKeyboardButton("📢 Hammaga xabar", callback_data="admin:broadcast"),
        InlineKeyboardButton("⬅️ Orqaga", callback_data="admin:back_main"),
    )
    return kb


def approve_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=admin_approve_factory.new(order_id=order_id)),
        InlineKeyboardButton("❌ Bekor qilish", callback_data=admin_cancel_order_factory.new(order_id=order_id)),
    )
    return kb


def view_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🔍 Ko'rish", callback_data=admin_view_order_factory.new(order_id=order_id)),
    )
    return kb


def user_remove_keyboard(user_pk: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🗑 O'chirish", callback_data=admin_remove_factory.new(user_pk=user_pk)))
    return kb


def confirm_broadcast_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Ha, yuborish", callback_data="broadcast:confirm"),
        InlineKeyboardButton("❌ Bekor", callback_data="broadcast:cancel"),
    )
    return kb


def cancel_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_flow"))
    return kb
