"""
Client bot FAQ + Contact + Prices handlers.
All navigation via inline callbacks (menu:faq, menu:contact, menu:prices).
"""
from telebot.states.asyncio.context import StateContext

from bots.client_bot.loader import handler
from bots.client_bot.keyboards.client import (
    main_menu_keyboard, faq_keyboard, faq_back_keyboard,
)
from bots.base.sender import Sender
from core.i18n import t
from core.callbacks import faq_factory
from apps.accounts.models import FAQItem, CompanyInfo


# ── FAQ ───────────────────────────────────────────────────────────────────────

@handler(callback=True, call='menu:faq')
async def client_faq(sender: Sender, state: StateContext):
    lang = sender.lang
    items = []
    async for item in FAQItem.objects.filter(is_active=True).aiterator():
        items.append(item)

    if not items:
        await sender.edit_text(t('faq_empty', lang), markup=main_menu_keyboard(lang))
        await sender.answer()
        return

    await sender.edit_text(t('faq_title', lang), markup=faq_keyboard(items, lang))
    await sender.answer()


@handler(callback=True, config=faq_factory.filter())
async def client_faq_answer(sender: Sender, state: StateContext):
    cb = faq_factory.parse(sender.msg.data)
    lang = sender.lang
    try:
        item = await FAQItem.objects.aget(pk=int(cb['item_id']), is_active=True)
    except FAQItem.DoesNotExist:
        await sender.answer(t('error_generic', lang), show_alert=True)
        return

    question = item.get_question(lang)
    answer = item.get_answer(lang)
    await sender.edit_text(
        f"❓ <b>{question}</b>\n\n{answer}",
        markup=faq_back_keyboard(lang),
    )
    await sender.answer()


@handler(callback=True, call='faq:back')
async def client_faq_back(sender: Sender, state: StateContext):
    lang = sender.lang
    items = []
    async for item in FAQItem.objects.filter(is_active=True).aiterator():
        items.append(item)
    await sender.edit_text(t('faq_title', lang), markup=faq_keyboard(items, lang))
    await sender.answer()


@handler(callback=True, call='faq:back_menu')
async def client_faq_back_menu(sender: Sender, state: StateContext):
    lang = sender.lang
    await sender.edit_text(t('main_menu', lang), markup=main_menu_keyboard(lang))
    await sender.answer()


# ── Contact ───────────────────────────────────────────────────────────────────

@handler(callback=True, call='menu:contact')
async def client_contact(sender: Sender, state: StateContext):
    lang = sender.lang
    info = await CompanyInfo.objects.filter(pk=1).afirst()
    if not info:
        await sender.answer(t('error_generic', lang), show_alert=True)
        return

    website_line = f"🌐 {info.website}" if info.website else ""
    await sender.edit_text(
        t('contact_info', lang,
          phone=info.phone,
          address=info.get_address(lang),
          website_line=website_line),
        markup=main_menu_keyboard(lang),
    )
    await sender.answer()


# ── Prices ────────────────────────────────────────────────────────────────────

@handler(callback=True, call='menu:prices')
async def client_prices(sender: Sender, state: StateContext):
    lang = sender.lang
    info = await CompanyInfo.objects.filter(pk=1).afirst()
    prices = info.get_prices(lang) if info else ''

    if not prices:
        await sender.edit_text(t('prices_not_set', lang), markup=main_menu_keyboard(lang))
        await sender.answer()
        return

    await sender.edit_text(t('prices_info', lang, prices=prices), markup=main_menu_keyboard(lang))
    await sender.answer()
