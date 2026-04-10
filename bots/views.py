import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

import telebot

logger = logging.getLogger(__name__)


async def process_webhook(request, token: str, expected_token: str, bot, bot_name: str):
    if token != expected_token:
        return HttpResponseForbidden("Invalid token")

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    try:
        update = telebot.types.Update.de_json(payload)
        await bot.process_new_updates([update])
    except Exception:
        logger.exception("[%s] Error processing", bot_name)

    return HttpResponse("OK")


@method_decorator(csrf_exempt, name="dispatch")
class MainBotWebhookView(View):

    async def post(self, request, token: str):
        import bots.main_bot.handlers  # noqa — registers handlers
        from bots.main_bot.loader import bot
        return await process_webhook(request, token, settings.MAIN_BOT_TOKEN, bot, "main_bot")

    async def get(self, request, token: str):
        if token != settings.MAIN_BOT_TOKEN:
            return HttpResponseForbidden("Invalid token")
        return HttpResponse("Main bot OK")


@method_decorator(csrf_exempt, name="dispatch")
class ClientBotWebhookView(View):


    async def post(self, request, token: str):
        import bots.client_bot.handlers  # noqa — registers handlers
        from bots.client_bot.loader import bot
        return await process_webhook(request, token, settings.CLIENT_BOT_TOKEN, bot, "client_bot")

    async def get(self, request, token: str):
        if token != settings.CLIENT_BOT_TOKEN:
            return HttpResponseForbidden("Invalid token")
        return HttpResponse("Client bot OK")
