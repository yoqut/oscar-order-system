"""
Telegram webhook endpoint.

Telegram sends POST requests to:
  /bot_app/webhook/<BOT_TOKEN>/

The token in the URL acts as a simple secret — if it doesn't match the
configured BOT_TOKEN, the request is rejected with 403.

Duplicate-update protection: Telegram may retry failed deliveries.
We deduplicate by update_id using an in-process LRU set.  For a
multi-worker deployment, replace with a shared Redis SETNX check.
"""
import json
import logging
import time
from collections import OrderedDict

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

import telebot

import bot_app.handlers  # noqa: F401 — registers all @bot_app decorators
from bot_app.core.loader import bot

logger = logging.getLogger(__name__)

# ── Deduplication cache ───────────────────────────────────────────────────────
# Keeps the last N processed update_ids to reject Telegram retries.
_DEDUP_MAXSIZE = 1000
_DEDUP_TTL = 60 * 10  # 10 minutes

# OrderedDict used as an LRU cache: {update_id: timestamp}
_seen_updates: OrderedDict[int, float] = OrderedDict()


def _is_duplicate(update_id: int) -> bool:
    now = time.monotonic()

    # Evict expired entries (oldest first)
    while _seen_updates:
        oldest_id, oldest_ts = next(iter(_seen_updates.items()))
        if now - oldest_ts > _DEDUP_TTL:
            _seen_updates.popitem(last=False)
        else:
            break

    if update_id in _seen_updates:
        return True

    # Trim to max size before inserting
    if len(_seen_updates) >= _DEDUP_MAXSIZE:
        _seen_updates.popitem(last=False)

    _seen_updates[update_id] = now
    return False


# ── Webhook view ──────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(View):

    async def dispatch(self, request, *args, **kwargs):
        return await super().dispatch(request, *args, **kwargs)

    async def post(self, request, token: str) -> HttpResponse:
        if token != settings.BOT_TOKEN:
            logger.warning("Webhook: invalid token from %s",
                           request.META.get("REMOTE_ADDR"))
            return HttpResponseForbidden("Invalid token")

        # Acknowledge immediately — Telegram expects < 1 s response time.
        # All heavy processing runs in the same async task but we return
        # 200 OK as soon as we accept the payload.
        try:
            body = request.body.decode("utf-8")
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.error("Webhook: malformed body — %s", exc)
            return HttpResponseBadRequest("Invalid JSON")

        update_id = payload.get("update_id")
        if update_id and _is_duplicate(update_id):
            logger.info("Webhook: duplicate update_id=%s, skipping", update_id)
            return HttpResponse("", status=200)

        try:
            update = telebot.types.Update.de_json(payload)
            await bot.process_new_updates([update])
        except Exception:
            logger.exception("Webhook: error processing update_id=%s", update_id)
            # Still return 200 — returning 4xx/5xx causes Telegram to retry,
            # which would trigger the same error in a loop.

        return HttpResponse("", status=200)

    async def get(self, request, token: str) -> HttpResponse:
        if token != settings.BOT_TOKEN:
            return HttpResponseForbidden("Invalid token")
        return HttpResponse("Oscar Agro Bot is running ✅", content_type="text/plain")
