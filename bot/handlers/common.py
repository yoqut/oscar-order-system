"""
Handles /start and routes users to their role-specific menus.
Also handles the /order_<id> deep-link for clients to view an order.
"""
import logging
from telebot import types
from django.conf import settings

from bot.loader import bot
from bot.utils.helpers import get_or_create_user
from bot.utils.state_manager import StateManager
from apps.accounts.models import TelegramUser, UserRole

logger = logging.getLogger(__name__)


@bot.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user = await get_or_create_user(message)
    await StateManager.clear(user.telegram_id)

    # Auto-promote configured super admins
    if user.telegram_id in settings.SUPER_ADMIN_IDS and user.role != UserRole.SUPER_ADMIN:
        user.role = UserRole.SUPER_ADMIN
        await user.asave(update_fields=['role', 'updated_at'])

    await _show_main_menu(message, user)


async def _show_main_menu(message: types.Message, user: TelegramUser):
    from bot.keyboards.sales_kb import sales_main_menu
    from bot.keyboards.agronomist_kb import agronomist_main_menu
    from bot.keyboards.admin_kb import admin_main_menu

    if user.role == UserRole.SUPER_ADMIN:
        await bot.send_message(
            message.chat.id,
            f"👑 Xush kelibsiz, <b>{user.full_name}</b>!\nAdmin paneli:",
            reply_markup=admin_main_menu(),
        )
    elif user.role == UserRole.SALES_MANAGER:
        await bot.send_message(
            message.chat.id,
            f"👋 Salom, <b>{user.full_name}</b>!\nSotuvchi paneli:",
            reply_markup=sales_main_menu(),
        )
    elif user.role == UserRole.AGRONOMIST:
        await bot.send_message(
            message.chat.id,
            f"🌱 Salom, <b>{user.full_name}</b>!\nAgronom paneli:",
            reply_markup=agronomist_main_menu(),
        )
    else:
        await bot.send_message(
            message.chat.id,
            f"👋 Salom, <b>{user.full_name}</b>!\n\n"
            "Siz bu bot orqali buyurtmalaringizni kuzatishingiz mumkin.\n"
            "Buyurtma yaratish uchun sotuvchiga murojaat qiling.",
        )


@bot.message_handler(commands=['order'])
async def cmd_order_deeplink(message: types.Message):
    """Handle /order_<id> — show order info to client."""
    parts = message.text.split('_', 1)
    if len(parts) != 2 or not parts[1].isdigit():
        await bot.send_message(message.chat.id, "❌ Noto'g'ri buyurtma raqami.")
        return

    order_id = int(parts[1])
    await _send_order_info(message.chat.id, order_id, message.from_user.id)


async def _send_order_info(chat_id: int, order_id: int, telegram_id: int):
    from apps.orders.models import Order
    from bot.utils.helpers import format_order_card

    try:
        order = await Order.objects.select_related(
            'agronomist', 'sales_manager', 'client'
        ).aget(pk=order_id)
    except Order.DoesNotExist:
        await bot.send_message(chat_id, "❌ Buyurtma topilmadi.")
        return

    # Only allow access to the client linked to this order (or admins)
    try:
        user = await TelegramUser.objects.aget(telegram_id=telegram_id)
    except TelegramUser.DoesNotExist:
        await bot.send_message(chat_id, "❌ Foydalanuvchi topilmadi.")
        return

    is_owner = order.client and order.client.telegram_id == telegram_id
    is_admin = user.role == UserRole.SUPER_ADMIN

    if not (is_owner or is_admin):
        await bot.send_message(chat_id, "⛔ Sizda bu buyurtmani ko'rish huquqi yo'q.")
        return

    text = format_order_card(order)

    # Append treatment summary if available
    try:
        details = order.treatment_details
        text += f"\n\n<b>Ishlov ma'lumotlari:</b>\n{details.get_summary()}"
    except Exception:
        pass

    await bot.send_message(chat_id, text)
