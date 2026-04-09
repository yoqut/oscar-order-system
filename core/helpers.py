"""
Shared helpers used across both bots.
"""
import logging
from telebot.async_telebot import AsyncTeleBot
from apps.accounts.models import TelegramUser, UserRole
from apps.notifications.models import NotificationLog, NotificationStatus
from apps.orders.models import Order, TimeSlot

logger = logging.getLogger(__name__)


async def notify_user(
    bot: AsyncTeleBot,
    telegram_id: int,
    text: str,
    reply_markup=None,
    parse_mode: str = 'HTML',
) -> bool:
    """Send a message and log it. Returns True on success."""
    try:
        msg = await bot.send_message(
            telegram_id,
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
        try:
            user = await TelegramUser.objects.aget(telegram_id=telegram_id)
            await NotificationLog.objects.acreate(
                recipient=user,
                message=text[:500],
                telegram_message_id=msg.message_id,
                status=NotificationStatus.SENT,
            )
        except TelegramUser.DoesNotExist:
            pass
        return True
    except Exception as exc:
        logger.error("notify_user failed telegram_id=%s: %s", telegram_id, exc)
        try:
            user = await TelegramUser.objects.aget(telegram_id=telegram_id)
            await NotificationLog.objects.acreate(
                recipient=user,
                message=text[:500],
                status=NotificationStatus.FAILED,
                error_message=str(exc)[:255],
            )
        except Exception:
            pass
        return False


async def notify_admins(
    bot: AsyncTeleBot,
    text: str,
    reply_markup=None,
) -> None:
    """Notify all active super admins."""
    async for admin in TelegramUser.objects.filter(
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    ).aiterator():
        await notify_user(bot, admin.telegram_id, text, reply_markup=reply_markup)


async def notify_sales_managers(
    bot: AsyncTeleBot,
    text: str,
    reply_markup=None,
) -> None:
    """Notify all active sales managers."""
    async for user in TelegramUser.objects.filter(
        role=UserRole.SALES_MANAGER,
        is_active=True,
    ).aiterator():
        await notify_user(bot, user.telegram_id, text, reply_markup=reply_markup)


async def broadcast(
    bot: AsyncTeleBot,
    text: str,
    role: str | None = None,
) -> int:
    """Broadcast to all active users (or specific role). Returns success count."""
    qs = TelegramUser.objects.filter(is_active=True)
    if role:
        qs = qs.filter(role=role)
    count = 0
    async for user in qs.aiterator():
        if await notify_user(bot, user.telegram_id, text):
            count += 1
    return count


def format_order_card(order: Order) -> str:
    """Format order summary as HTML for bot messages."""
    slot = dict(TimeSlot.choices).get(order.time_slot, order.time_slot) if order.time_slot else '—'
    phone2 = f" / {order.phone2}" if order.phone2 else ""
    agro_name = order.agronomist.full_name if order.agronomist_id else '—'
    sales_name = order.sales_manager.full_name if order.sales_manager_id else '—'
    return (
        f"📋 <b>Buyurtma #{order.pk}</b>\n"
        f"👤 Mijoz: {order.client_name}\n"
        f"📞 Tel: {order.phone1}{phone2}\n"
        f"🌳 Daraxt: {order.tree_count}\n"
        f"⏰ Vaqt: {slot}\n"
        f"🔴 Muammo: {order.problem}\n"
        f"📍 Manzil: {order.address}\n"
        f"🌱 Agronom: {agro_name}\n"
        f"🛒 Sotuvchi: {sales_name}\n"
        f"📊 Holat: {order.status}"
    )


def format_order_card_lang(order: Order, lang: str) -> str:
    """Format order card in user's language (for client bot)."""
    from core.i18n import t, TRANSLATIONS
    slot = dict(TimeSlot.choices).get(order.time_slot, order.time_slot) if order.time_slot else '—'
    phone2 = f" / {order.phone2}" if order.phone2 else ""
    status_key = f"status_{order.status}"
    status_text = t(status_key, lang)
    return (
        f"📋 <b>#{order.pk}</b>\n"
        f"🔴 {order.problem}\n"
        f"📍 {order.address}\n"
        f"🌳 {order.tree_count}\n"
        f"📞 {order.phone1}{phone2}\n"
        f"⏰ {slot}\n"
        f"📊 {status_text}"
    )
