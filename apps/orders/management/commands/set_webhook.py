import asyncio
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Register the Telegram webhook URL with Telegram servers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete (remove) the current webhook instead of setting it',
        )

    def handle(self, *args, **options):  # ✅ SYNC
        from bot.loader import bot

        if options['delete']:
            asyncio.run(self._delete_webhook(bot))
        else:
            asyncio.run(self._set_webhook(bot))

    async def _set_webhook(self, bot):
        if not settings.BOT_TOKEN:
            self.stderr.write(self.style.ERROR('BOT_TOKEN is not configured.'))
            return
        if not settings.WEBHOOK_BASE_URL:
            self.stderr.write(self.style.ERROR('WEBHOOK_BASE_URL is not configured.'))
            return

        webhook_url = f"{settings.WEBHOOK_BASE_URL.rstrip('/')}/bot/webhook/{settings.BOT_TOKEN}/"
        await bot.set_webhook(webhook_url)

        self.stdout.write(self.style.SUCCESS(f'Webhook set: {webhook_url}'))

    async def _delete_webhook(self, bot):
        await bot.delete_webhook()
        self.stdout.write(self.style.SUCCESS('Webhook deleted.'))