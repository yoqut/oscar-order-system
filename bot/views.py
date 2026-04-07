"""
Telegram webhook endpoint.

Telegram sends POST requests to:
  /bot/webhook/<BOT_TOKEN>/

The token in the URL acts as a simple secret — if it doesn't match the
configured BOT_TOKEN, the request is rejected with 403.
"""
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

import telebot

# Importing handlers registers all @bot decorators before the first update.
import bot.handlers  # noqa: F401
from bot.loader import bot

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(View):

    async def dispatch(self, request, *args, **kwargs):
        return await super().dispatch(request, *args, **kwargs)

    async def post(self, request, token: str):
        if token != settings.BOT_TOKEN:
            logger.warning("Webhook received with invalid token")
            return HttpResponseForbidden("Invalid token")

        try:
            body = request.body.decode('utf-8')
            update = telebot.types.Update.de_json(json.loads(body))
            await bot.process_new_updates([update])
        except json.JSONDecodeError:
            logger.error("Webhook received non-JSON body")
            return HttpResponseBadRequest("Invalid JSON")
        except Exception:
            logger.exception("Error processing webhook update")

        return HttpResponse('', status=200)

    async def get(self, request, token: str):
        return HttpResponse('Oscar Agro Bot is running ✅', content_type='text/plain')