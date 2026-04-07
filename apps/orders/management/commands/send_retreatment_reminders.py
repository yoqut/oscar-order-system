"""
Management command: send re-treatment reminders to clients and agronomists.

Schedule via cron (runs daily, e.g. 08:00):
    0 8 * * * /path/to/venv/bin/python /path/to/manage.py send_retreatment_reminders
"""
import asyncio
import logging
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from apps.orders.models import TreatmentDetails

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send Telegram reminders for scheduled re-treatments (run daily via cron)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=1,
            help='Send reminder for re-treatments scheduled N days from today (default: 1)',
        )

    def handle(self, *args, **options):
        asyncio.run(self._run(options['days_ahead']))

    async def _run(self, days_ahead: int):
        from bot.loader import bot
        from bot.utils.helpers import notify_user

        target_date = date.today() + timedelta(days=days_ahead)
        self.stdout.write(f'Sending re-treatment reminders for {target_date}...')

        qs = TreatmentDetails.objects.select_related(
            'order__client', 'order__agronomist', 'order__sales_manager'
        ).filter(
            re_treatment_needed=True,
            re_treatment_date=target_date,
            re_treatment_notified=False,
        )

        count = 0
        async for detail in qs.aiterator():
            order = detail.order
            sent = False

            # Notify client if linked
            if order.client:
                client_msg = (
                    f"⏰ <b>Qayta ishlov eslatmasi</b>\n\n"
                    f"Order #{order.pk} bo'yicha ertaga ({target_date}) qayta ishlov "
                    f"rejalashtirilgan.\n\n"
                    f"Manzil: {order.address}\n"
                    f"Muammo: {order.problem}"
                )
                await notify_user(bot, order.client.telegram_id, client_msg)
                sent = True

            # Notify agronomist
            agro_msg = (
                f"⏰ <b>Qayta ishlov eslatmasi</b>\n\n"
                f"Order #{order.pk} — {order.client_name}\n"
                f"Sana: {target_date}\n"
                f"Manzil: {order.address}\n"
                f"Telefon: {order.phone1}"
            )
            await notify_user(bot, order.agronomist.telegram_id, agro_msg)
            sent = True

            if sent:
                await TreatmentDetails.objects.filter(pk=detail.pk).aupdate(re_treatment_notified=True)
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Sent {count} re-treatment reminder(s).'))
