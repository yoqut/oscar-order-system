"""
Client bot catch-all text router.
Handles all remaining state-based text input.
MUST be imported last.
"""
import logging
import re
from telebot.states.asyncio.context import StateContext

from bots.client_bot.loader import bot, handler
from bots.client_bot.states import OrderStates, RatingStates
from bots.client_bot.keyboards.client import main_menu_keyboard, cancel_keyboard
from bots.base.sender import Sender
from core.i18n import t
from core.helpers import notify_user
from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order, OrderStatus, Feedback

logger = logging.getLogger(__name__)


async def _get_client(telegram_id: int) -> TelegramUser | None:
    try:
        return await TelegramUser.objects.aget(telegram_id=telegram_id, role=UserRole.CLIENT, is_active=True)
    except TelegramUser.DoesNotExist:
        return None


# ── Cancel reason (order reject by client) ────────────────────────────────────

@handler(state=OrderStates.ENTER_CANCEL_REASON)
async def client_enter_cancel_reason(sender: Sender, state: StateContext):
    reason = sender.msg.text.strip() if sender.msg.text else ''
    async with state.data() as data:
        lang = data.get('client_lang', sender.lang)
        order_id = data.get('rejecting_order_id')

    if not reason:
        await sender.text(t('ask_cancel_reason', lang))
        return

    await state.delete()

    if order_id:
        try:
            order = await Order.objects.select_related('agronomist', 'sales_manager').aget(pk=order_id)
            await Order.objects.filter(pk=order_id).aupdate(
                status=OrderStatus.CANCELLED,
                cancel_reason=reason,
            )
            await sender.text(t('order_rejected_msg', lang), markup=main_menu_keyboard(lang))

            # Notify staff
            from bots.main_bot.loader import bot as main_bot
            if order.sales_manager_id:
                await notify_user(
                    main_bot, order.sales_manager.telegram_id,
                    f"❌ Mijoz buyurtma #{order_id}ni rad etdi.\nSabab: {reason}",
                )
            if order.agronomist_id:
                await notify_user(
                    main_bot, order.agronomist.telegram_id,
                    f"❌ Buyurtma #{order_id} bekor qilindi.\nSabab: {reason}",
                )
        except Order.DoesNotExist:
            await sender.text(t('error_generic', lang), markup=main_menu_keyboard(lang))
    else:
        await sender.text(t('error_generic', lang), markup=main_menu_keyboard(lang))


# ── Reject reason (service rejection) ────────────────────────────────────────

@handler(state=OrderStates.ENTER_REJECT_REASON)
async def client_enter_reject_reason(sender: Sender, state: StateContext):
    reason = sender.msg.text.strip() if sender.msg.text else ''
    async with state.data() as data:
        lang = data.get('client_lang', sender.lang)
        order_id = data.get('rejecting_order_id')

    if not reason:
        await sender.text(t('ask_reject_reason', lang))
        return

    await state.delete()

    if order_id:
        try:
            order = await Order.objects.select_related('agronomist', 'sales_manager').aget(pk=order_id)
            await Order.objects.filter(pk=order_id).aupdate(
                status=OrderStatus.CLIENT_REJECTED,
                cancel_reason=reason,
            )
            await sender.text(t('service_rejected_msg', lang), markup=main_menu_keyboard(lang))

            from bots.main_bot.loader import bot as main_bot
            from core.helpers import notify_admins
            if order.agronomist_id:
                await notify_user(
                    main_bot, order.agronomist.telegram_id,
                    f"❌ Mijoz xizmatni qabul qilmadi (#{order_id}).\nSabab: {reason}",
                )
            if order.sales_manager_id:
                await notify_user(
                    main_bot, order.sales_manager.telegram_id,
                    f"❌ Buyurtma #{order_id} mijoz tomonidan rad etildi.\nSabab: {reason}",
                )
            await notify_admins(
                main_bot,
                f"❌ Buyurtma #{order_id} mijoz tomonidan rad etildi.\nSabab: {reason}",
            )
        except Order.DoesNotExist:
            await sender.text(t('error_generic', lang), markup=main_menu_keyboard(lang))
    else:
        await sender.text(t('error_generic', lang), markup=main_menu_keyboard(lang))


# ── Rating comment ────────────────────────────────────────────────────────────

@handler(state=RatingStates.ENTER_COMMENT)
async def client_enter_comment(sender: Sender, state: StateContext):
    comment = sender.msg.text.strip() if sender.msg.text else ''
    async with state.data() as data:
        lang = data.get('client_lang', sender.lang)
        order_id = data.get('rating_order_id')
        rating = data.get('rating', 5)

    await state.delete()

    client = await _get_client(sender.user_id)
    if order_id and client:
        try:
            await Feedback.objects.aupdate_or_create(
                order_id=order_id,
                defaults={
                    'client': client,
                    'rating': rating,
                    'comment': comment or None,
                },
            )
        except Exception as exc:
            logger.error("Feedback save failed: %s", exc)

    stars = '⭐' * rating
    await sender.text(t('rated_msg', lang, stars=stars), markup=main_menu_keyboard(lang))


# ── Default catch-all ─────────────────────────────────────────────────────────

@handler(func=lambda m: True)
async def client_unknown(sender: Sender, state: StateContext):
    lang = sender.lang
    current_state = await state.get()
    if current_state:
        return  # Let specific state handlers deal with it

    client = await _get_client(sender.user_id)
    if not client:
        await sender.text(t('error_not_registered', lang))
        return

    await sender.text(t('unknown_command', lang), markup=main_menu_keyboard(lang))
