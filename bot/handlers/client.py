"""
Client flow:
  Accept/Cancel order notification → Confirm/Reject service → Rate → Leave feedback
"""
import logging
from telebot import types

from bot.loader import bot
from bot.states import ClientStates
from bot.utils.state_manager import StateManager
from bot.utils.helpers import notify_user, notify_admins
from bot.keyboards.client_kb import (
    rating_keyboard, skip_comment_keyboard,
)
from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order, OrderStatus, Feedback

logger = logging.getLogger(__name__)


async def _get_client(telegram_id: int):
    try:
        return await TelegramUser.objects.aget(telegram_id=telegram_id, is_active=True)
    except TelegramUser.DoesNotExist:
        return None


# ── Accept order notification ─────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("client:accept:"))
async def client_cb_accept_order(call: types.CallbackQuery):
    order_id = int(call.data.split(":")[2])
    client = await _get_client(call.from_user.id)

    if not client:
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    try:
        order = await Order.objects.select_related('agronomist', 'sales_manager').aget(pk=order_id)
    except Order.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Buyurtma topilmadi")
        return

    # Link client to order if not linked yet
    if order.client is None:
        order.client = client
        await order.asave(update_fields=['client', 'updated_at'])

    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    await bot.send_message(
        call.message.chat.id,
        f"✅ Buyurtma #{order_id} qabul qilindi.\nAgronom siz bilan bog'lanadi."
    )

    notify_text = (
        f"✅ Mijoz buyurtma #{order_id}ni qabul qildi.\n"
        f"Mijoz: {client.full_name}"
    )
    await notify_user(bot, order.agronomist.telegram_id, notify_text)
    await notify_user(bot, order.sales_manager.telegram_id, notify_text)
    await bot.answer_callback_query(call.id, "✅ Qabul qilindi!")


# ── Cancel order (from notification) ─────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("client:cancel:"))
async def client_cb_cancel_order(call: types.CallbackQuery):
    order_id = int(call.data.split(":")[2])
    client = await _get_client(call.from_user.id)

    if not client:
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    await StateManager.set_state(
        call.from_user.id,
        ClientStates.ENTER_CANCEL_REASON,
        data={'order_id': order_id},
    )
    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    await bot.send_message(
        call.message.chat.id,
        f"❌ Buyurtma #{order_id}ni bekor qilish sababini yozing:"
    )
    await bot.answer_callback_query(call.id)


# ── Confirm service ───────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("client:confirm:"))
async def client_cb_confirm_service(call: types.CallbackQuery):
    order_id = int(call.data.split(":")[2])
    client = await _get_client(call.from_user.id)

    if not client:
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    try:
        order = await Order.objects.select_related('agronomist', 'sales_manager').aget(pk=order_id)
    except Order.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Buyurtma topilmadi")
        return

    if order.status != OrderStatus.COMPLETED:
        await bot.answer_callback_query(call.id, "⚠️ Buyurtma hali yakunlanmagan")
        return

    order.status = OrderStatus.CLIENT_CONFIRMED
    await order.asave(update_fields=['status', 'updated_at'])

    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    await bot.send_message(
        call.message.chat.id,
        f"✅ Xizmat tasdiqlandi! Rahmat.\n\nIltimos, xizmatimizni baholang:",
        reply_markup=rating_keyboard(order_id),
    )

    confirm_text = f"✅ Mijoz buyurtma #{order_id} xizmatini tasdiqladi."
    await notify_user(bot, order.agronomist.telegram_id, confirm_text)
    await notify_user(bot, order.sales_manager.telegram_id, confirm_text)
    await notify_admins(bot, confirm_text)
    await bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")


# ── Reject service ────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("client:reject:"))
async def client_cb_reject_service(call: types.CallbackQuery):
    order_id = int(call.data.split(":")[2])
    client = await _get_client(call.from_user.id)

    if not client:
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    try:
        order = await Order.objects.select_related('agronomist', 'sales_manager').aget(pk=order_id)
    except Order.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Buyurtma topilmadi")
        return

    order.status = OrderStatus.CLIENT_REJECTED
    await order.asave(update_fields=['status', 'updated_at'])

    await StateManager.set_state(
        call.from_user.id,
        ClientStates.ENTER_CANCEL_REASON,
        data={'order_id': order_id, 'is_rejection': True},
    )
    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    await bot.send_message(
        call.message.chat.id,
        f"❌ Rad etildi. Iltimos, sababini yozing:"
    )
    await bot.answer_callback_query(call.id)


# ── Rating ────────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("rate:"))
async def client_cb_rate(call: types.CallbackQuery):
    parts = call.data.split(":")
    order_id = int(parts[1])
    rating = int(parts[2])

    client = await _get_client(call.from_user.id)
    if not client:
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    await StateManager.set_state(
        call.from_user.id,
        ClientStates.ENTER_COMMENT,
        data={'order_id': order_id, 'rating': rating},
    )
    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    await bot.send_message(
        call.message.chat.id,
        f"{'⭐' * rating} Reyting: {rating}/5\n\nIzoh qoldiring (ixtiyoriy):",
        reply_markup=skip_comment_keyboard(),
    )
    await bot.answer_callback_query(call.id)


# ── Skip comment ──────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "comment:skip")
async def client_cb_skip_comment(call: types.CallbackQuery):
    client = await _get_client(call.from_user.id)
    if not client:
        await bot.answer_callback_query(call.id)
        return

    state, data = await StateManager.get_state_and_data(call.from_user.id)
    if state != ClientStates.ENTER_COMMENT:
        await bot.answer_callback_query(call.id)
        return

    await _save_feedback(call.from_user.id, call.message, data, comment=None)
    await bot.answer_callback_query(call.id, "✅ Baholandi!")


# ── Text router for client states ─────────────────────────────────────────────

@bot.message_handler(func=lambda m: True, content_types=['text'])
async def client_text_router(message: types.Message):
    client = await _get_client(message.from_user.id)
    if not client or client.role not in (UserRole.CLIENT,):
        return

    state, data = await StateManager.get_state_and_data(message.from_user.id)
    if not state or not state.startswith("client:"):
        return

    text = message.text.strip()

    if state == ClientStates.ENTER_CANCEL_REASON:
        order_id = data.get('order_id')
        is_rejection = data.get('is_rejection', False)

        try:
            order = await Order.objects.select_related('agronomist', 'sales_manager').aget(pk=order_id)
        except Order.DoesNotExist:
            await StateManager.clear(message.from_user.id)
            await bot.send_message(message.chat.id, "❌ Buyurtma topilmadi.")
            return

        if not is_rejection:
            order.status = OrderStatus.CANCELLED
            order.cancel_reason = text
            await order.asave(update_fields=['status', 'cancel_reason', 'updated_at'])

        await StateManager.clear(message.from_user.id)
        action = "rad etildi" if is_rejection else "bekor qilindi"
        await bot.send_message(
            message.chat.id,
            f"✅ Buyurtma #{order_id} {action}.\n\nSabab qayd etildi. Operator siz bilan bog'lanadi."
        )

        notify_text = (
            f"{'❌ Mijoz xizmatni rad etdi' if is_rejection else '❌ Mijoz buyurtmani bekor qildi'}\n"
            f"Order #{order_id}\nMijoz: {client.full_name}\nSabab: {text}"
        )
        await notify_user(bot, order.agronomist.telegram_id, notify_text)
        await notify_user(bot, order.sales_manager.telegram_id, notify_text)
        await notify_admins(bot, notify_text)

    elif state == ClientStates.ENTER_COMMENT:
        await _save_feedback(message.from_user.id, message, data, comment=text)


async def _save_feedback(telegram_id: int, message, data: dict, comment: str = None):
    order_id = data.get('order_id')
    rating = data.get('rating')
    client = await _get_client(telegram_id)

    try:
        order = await Order.objects.aget(pk=order_id)
        await Feedback.objects.aupdate_or_create(
            order=order,
            defaults={'client': client, 'rating': rating, 'comment': comment},
        )
    except Exception as exc:
        logger.error("Failed to save feedback: %s", exc)

    await StateManager.clear(telegram_id)
    await bot.send_message(
        message.chat.id,
        f"🙏 Rahmat! Sizning {'⭐' * rating} reytingingiz va fikringiz saqlandi."
    )
