import logging
import re
from telebot import types
from telebot.states.asyncio.context import StateContext

from ....core.loader import bot
from ....core.use_states import SalesStates
from ....keyboards.sales_kb import agronomist_list_keyboard

from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order

logger = logging.getLogger(__name__)


PHONE_RE = re.compile(r'^\+?[0-9]{9,15}$')


# ── My orders ─────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data == "my_orders", is_sales=True)
async def sales_my_orders(message: types.CallbackQuery):

    orders = [o async for o in Order.objects.filter(
        sales_manager__telegram_id=message.from_user.id
    ).order_by('-created_at').aiterator()]

    if not orders:
        await bot.send_message(message.message.chat.id, "📭 Hali buyurtma yo'q.")
        return

    text = f"📋 <b>Sizning buyurtmalaringiz ({len(orders)} ta):</b>\n\n"
    for order in orders[:20]:
        text += f"• #{order.pk} — {order.client_name} [{order.get_status_display()}]\n"
    await bot.send_message(message.message.chat.id, text)


# ── Entry: start order ────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data == "create_order", is_sales=True)
async def sales_start_order(message: types.CallbackQuery, state: StateContext):

    agronomists = [u async for u in TelegramUser.objects.filter(
        role=UserRole.AGRONOMIST, is_active=True
    ).aiterator()]

    if not agronomists:
        await bot.send_message(
            message.message.chat.id,
            "⚠️ Hozircha aktiv agronom yo'q. Avval admin agronom qo'shishi kerak.",
        )
        return

    await state.set(SalesStates.SELECT_AGRONOMIST)
    await bot.edit_message_text(
        "🌱 Agronomni tanlang:",
        message.message.chat.id,
        message.message.message_id,
        reply_markup=agronomist_list_keyboard(agronomists),
    )
