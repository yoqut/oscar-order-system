"""
Set or delete webhooks for both bots.

Usage:
    python manage.py set_webhook             # Set both webhooks
    python manage.py set_webhook --delete    # Delete both webhooks
    python manage.py set_webhook --bot main  # Only main bot
    python manage.py set_webhook --bot client # Only client bot
"""
import asyncio
from django.conf import settings
from django.core.management.base import BaseCommand
from telebot.async_telebot import AsyncTeleBot

BOTS = {
    'main': {
        'token_attr': 'MAIN_BOT_TOKEN',
        'path': 'bots/main/webhook',
        'label': 'Main Bot (Staff)',
    },
    'client': {
        'token_attr': 'CLIENT_BOT_TOKEN',
        'path': 'bots/client/webhook',
        'label': 'Client Bot',
    },
}


class Command(BaseCommand):
    help = 'Set or delete Telegram webhooks for both bots'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete webhooks instead of setting them',
        )
        parser.add_argument(
            '--bot',
            choices=['main', 'client', 'both'],
            default='both',
            help='Which bot to configure (default: both)',
        )

    def handle(self, *args, **options):
        base_url = getattr(settings, 'WEBHOOK_BASE_URL', '').rstrip('/')
        if not base_url and not options['delete']:
            self.stderr.write(self.style.ERROR("❌ WEBHOOK_BASE_URL is not set in .env"))
            return

        bots_to_configure = (
            list(BOTS.items())
            if options['bot'] == 'both'
            else [(options['bot'], BOTS[options['bot']])]
        )

        asyncio.run(self._run(bots_to_configure, base_url, options['delete']))

    async def _run(self, bots_to_configure, base_url, delete):
        for _, config in bots_to_configure:
            token = getattr(settings, config['token_attr'], '')
            label = config['label']

            if not token:
                self.stderr.write(f"⚠️  {label}: token not set, skipping.")
                continue

            bot = AsyncTeleBot(token)

            try:
                if delete:
                    await bot.delete_webhook()
                    self.stdout.write(self.style.SUCCESS(f"✅ {label}: webhook deleted."))
                else:
                    url = f"{base_url}/{config['path']}/{token}/"

                    await bot.set_webhook(
                        url=url
                    )

                    info = await bot.get_webhook_info()

                    self.stdout.write(self.style.SUCCESS(
                        f"✅ {label}: webhook set\n"
                        f"   URL: {url}\n"
                        f"   Pending updates: {info.pending_update_count}"
                    ))

            finally:
                # 🔥 MUHIM FIX
                await bot.close_session()
