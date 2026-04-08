"""
Shared utility functions used across bot_app handlers.
"""
import logging
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from apps.accounts.models import TelegramUser, UserRole
from apps.notifications.models import NotificationLog, NotificationStatus

logger = logging.getLogger(__name__)


async def get_or_create_user(message: types.Message | types.CallbackQuery) -> TelegramUser:
    """Register user on first contact; update name/username on subsequent messages."""
    tg = message.from_user
    full_name = f"{tg.first_name or ''} {tg.last_name or ''}".strip() or tg.username or str(tg.id)

    user, created = await TelegramUser.objects.aupdate_or_create(
        telegram_id=tg.id,
        defaults={
            'username': tg.username,
            'full_name': full_name,
        },
    )
    return user


async def notify_user(
    bot: AsyncTeleBot,
    telegram_id: int,
    text: str,
    reply_markup=None,
    parse_mode: str = 'HTML',
) -> bool:
    """
    Send a message and log it to NotificationLog.
    Returns True on success, False on failure.
    """
    try:
        msg = await bot.send_message(
            telegram_id,
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        try:
            user = await TelegramUser.objects.aget(telegram_id=telegram_id)
            await NotificationLog.objects.acreate(
                recipient=user,
                message=text,
                telegram_message_id=msg.message_id,
                status=NotificationStatus.SENT,
            )
        except TelegramUser.DoesNotExist:
            pass
        return True
    except Exception as exc:
        logger.error("Failed to notify telegram_id=%s: %s", telegram_id, exc)
        try:
            user = await TelegramUser.objects.aget(telegram_id=telegram_id)
            await NotificationLog.objects.acreate(
                recipient=user,
                message=text,
                status=NotificationStatus.FAILED,
                error_message=str(exc),
            )
        except Exception:
            pass
        return False


async def broadcast(bot: AsyncTeleBot, text: str, role: str = None) -> int:
    """
    Send message to all active users (or a specific role subset).
    Returns count of successful deliveries.
    """
    qs = TelegramUser.objects.filter(is_active=True)
    if role:
        qs = qs.filter(role=role)

    count = 0
    async for user in qs.aiterator():
        if await notify_user(bot, user.telegram_id, text):
            count += 1
    return count


async def get_admins(bot: AsyncTeleBot = None):
    """Return all active super admins."""
    admins = []
    async for admin in TelegramUser.objects.filter(
        role=UserRole.SUPER_ADMIN, is_active=True
    ).aiterator():
        admins.append(admin)
    return admins


async def notify_admins(bot: AsyncTeleBot, text: str, reply_markup=None):
    """Notify all active super admins."""
    admins = await get_admins()
    for admin in admins:
        await notify_user(bot, admin.telegram_id, text, reply_markup=reply_markup)


def format_order_card(order) -> str:
    slot = order.get_time_slot_display()
    phone2 = f" / {order.phone2}" if order.phone2 else ""
    return (
        f"📋 <b>Order #{order.pk}</b>\n"
        f"👤 Mijoz: {order.client_name}\n"
        f"📞 Tel: {order.phone1}{phone2}\n"
        f"🌳 Daraxt soni: {order.tree_count}\n"
        f"⏰ Vaqt: {slot}\n"
        f"🔴 Muammo: {order.problem}\n"
        f"📍 Manzil: {order.address}\n"
        f"📊 Holat: {order.get_status_display()}"
    )
