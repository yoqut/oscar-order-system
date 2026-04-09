"""
Webhook views for both bots.

Telegram sends POST to:
  /bots/main/webhook/<MAIN_BOT_TOKEN>/
  /bots/client/webhook/<CLIENT_BOT_TOKEN>/

Token in URL authenticates the request.
Redis-based deduplication prevents processing Telegram retries.
"""
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

import telebot

from core.locks import try_lock

logger = logging.getLogger(__name__)


async def _process_webhook(request, token: str, expected_token: str, bot, bot_name: str):
    if token != expected_token:
        logger.warning("[%s] Invalid webhook token from %s", bot_name, request.META.get('REMOTE_ADDR'))
        return HttpResponseForbidden("Invalid token")

    try:
        body = request.body.decode('utf-8')
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.error("[%s] Malformed body: %s", bot_name, exc)
        return HttpResponseBadRequest("Invalid JSON")

    update_id = payload.get('update_id')

    # Redis-based deduplication (works across multiple workers)
    if update_id:
        lock_key = f"update:{bot_name}:{update_id}"
        if not await try_lock(lock_key, ttl=60):
            logger.info("[%s] Duplicate update_id=%s, skipping", bot_name, update_id)
            return HttpResponse("", status=200)

    try:
        update = telebot.types.Update.de_json(payload)
        await bot.process_new_updates([update])
    except Exception:
        logger.exception("[%s] Error processing update_id=%s", bot_name, update_id)

    return HttpResponse("", status=200)


@method_decorator(csrf_exempt, name='dispatch')
class MainBotWebhookView(View):

    async def dispatch(self, request, *args, **kwargs):
        return await super().dispatch(request, *args, **kwargs)

    async def post(self, request, token: str) -> HttpResponse:
        import bots.main_bot.handlers  # noqa — registers handlers
        from bots.main_bot.loader import bot
        return await _process_webhook(
            request, token, settings.MAIN_BOT_TOKEN, bot, 'main_bot'
        )

    async def get(self, request, token: str) -> HttpResponse:
        if token != settings.MAIN_BOT_TOKEN:
            return HttpResponseForbidden("Invalid token")
        return HttpResponse("Oscar Agro Main Bot ✅", content_type='text/plain')


@method_decorator(csrf_exempt, name='dispatch')
class ClientBotWebhookView(View):

    async def dispatch(self, request, *args, **kwargs):
        return await super().dispatch(request, *args, **kwargs)

    async def post(self, request, token: str) -> HttpResponse:
        import bots.client_bot.handlers  # noqa — registers handlers
        from bots.client_bot.loader import bot
        return await _process_webhook(
            request, token, settings.CLIENT_BOT_TOKEN, bot, 'client_bot'
        )

    async def get(self, request, token: str) -> HttpResponse:
        if token != settings.CLIENT_BOT_TOKEN:
            return HttpResponseForbidden("Invalid token")
        return HttpResponse("Oscar Agro Client Bot ✅", content_type='text/plain')
