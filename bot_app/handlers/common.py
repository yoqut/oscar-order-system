"""
Handles /start and routes users to their role-specific menus.
Also handles the /order_<id> deep-link for clients to view an order.
"""
import logging
from telebot import types

from ..core.loader import bot
from apps.accounts.models import TelegramUser, UserRole

logger = logging.getLogger(__name__)


@bot.message_handler(commands=['order'])
async def cmd_order_deeplink(message: types.Message):
    parts = message.text.split('_', 1)
    if len(parts) != 2 or not parts[1].isdigit():
        await bot.send_message(message.chat.id, "❌ Noto'g'ri buyurtma raqami.")
        return
    await _send_order_info(message.chat.id, int(parts[1]), message.from_user.id)


async def _send_order_info(chat_id: int, order_id: int, telegram_id: int):
    from apps.orders.models import Order
    from bot_app.utils.helpers import format_order_card

    try:
        order = await Order.objects.select_related(
            'agronomist', 'sales_manager', 'client'
        ).aget(pk=order_id)
    except Order.DoesNotExist:
        await bot.send_message(chat_id, "❌ Buyurtma topilmadi.")
        return

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
    try:
        details = order.treatment_details
        text += f"\n\n<b>Ishlov ma'lumotlari:</b>\n{details.get_summary()}"
    except Exception:
        pass

    await bot.send_message(chat_id, text)
