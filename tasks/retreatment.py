"""
Celery task: send re-treatment reminders.

Schedule via Django admin (django-celery-beat):
  Task: tasks.retreatment.send_retreatment_reminders
  Cron: every day at 09:00

Or add to settings:
  CELERY_BEAT_SCHEDULE = {
      'retreatment-reminders': {
          'task': 'tasks.retreatment.send_retreatment_reminders',
          'schedule': crontab(hour=9, minute=0),
      },
  }
"""
import asyncio
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='tasks.retreatment.send_retreatment_reminders', bind=True, max_retries=3)
def send_retreatment_reminders(self):
    """
    Send re-treatment reminders to clients whose re-treatment date is tomorrow.
    Marks notifications as sent to avoid duplicates.
    """
    try:
        asyncio.run(_async_send_retreatment_reminders())
    except Exception as exc:
        logger.error("send_retreatment_reminders failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * 10)


async def _async_send_retreatment_reminders():
    import django
    django.setup()

    from apps.orders.models import TreatmentDetails, Order
    from apps.accounts.models import TelegramUser
    from bots.client_bot.loader import bot as client_bot
    from bots.main_bot.loader import bot as main_bot
    from core.helpers import notify_user
    from core.i18n import t

    tomorrow = timezone.now().date() + timedelta(days=1)
    today = timezone.now().date()

    count = 0
    async for td in TreatmentDetails.objects.filter(
        re_treatment_needed=True,
        re_treatment_notified=False,
        re_treatment_date__in=[tomorrow, today],
    ).select_related('order__client', 'order__agronomist', 'order__sales_manager').aiterator():
        order = td.order

        # Notify client (via client bot)
        if order.client_id and order.client.is_active:
            lang = order.client.language or 'uz'
            date_str = td.re_treatment_date.strftime('%d.%m.%Y')
            text = t('retreatment_reminder', lang,
                     order_id=order.pk,
                     date=date_str)
            await notify_user(client_bot, order.client.telegram_id, text)

        # Notify agronomist (via main bot)
        if order.agronomist_id and order.agronomist.is_active:
            date_str = td.re_treatment_date.strftime('%d.%m.%Y')
            await notify_user(
                main_bot, order.agronomist.telegram_id,
                f"🔔 Qayta ishlov eslatmasi!\n\n"
                f"Buyurtma #{order.pk} — {order.client_name}\n"
                f"📅 Sana: {date_str}\n"
                f"📞 Tel: {order.phone1}",
            )

        # Mark as notified
        await TreatmentDetails.objects.filter(pk=td.pk).aupdate(re_treatment_notified=True)
        count += 1

    logger.info("Retreatment reminders sent: %d", count)
    return count
