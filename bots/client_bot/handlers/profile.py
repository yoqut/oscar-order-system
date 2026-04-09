"""
Client profile — view, edit name/phone, change language.
"""
import re
from telebot.states.asyncio.context import StateContext

from bots.client_bot.loader import handler
from bots.client_bot.states import ProfileStates
from bots.client_bot.keyboards.client import (
    main_menu_keyboard, profile_keyboard, language_keyboard,
    share_phone_keyboard
)
from bots.base.sender import Sender
from core.i18n import t, set_user_lang, LANG_NAMES
from apps.accounts.models import TelegramUser, UserRole

PHONE_RE = re.compile(r'^\+?[0-9]{9,15}$')


async def _get_client(telegram_id: int) -> TelegramUser | None:
    try:
        return await TelegramUser.objects.aget(telegram_id=telegram_id, role=UserRole.CLIENT, is_active=True)
    except TelegramUser.DoesNotExist:
        return None


# ── View profile ──────────────────────────────────────────────────────────────

@handler(func=lambda m: m.text and m.text in [
    t('btn_profile', l) for l in ['uz', 'ru', 'uz_kr', 'en']
])
async def client_profile(sender: Sender, state: StateContext):
    await state.delete()
    lang = sender.lang
    client = await _get_client(sender.user_id)
    if not client:
        await sender.text(t('error_not_registered', lang))
        return

    lang_name = LANG_NAMES.get(client.language, client.language)
    date_str = client.created_at.strftime('%d.%m.%Y') if client.created_at else '—'

    await sender.text(
        t('profile_view', lang,
          name=client.full_name,
          phone=client.phone or '—',
          lang=lang_name,
          date=date_str),
        markup=profile_keyboard(lang),
    )


# ── Edit name ─────────────────────────────────────────────────────────────────

@handler(callback=True, call='profile:edit_name')
async def profile_edit_name_start(sender: Sender, state: StateContext):
    lang = sender.lang
    await state.set(ProfileStates.EDIT_NAME)
    await state.add_data(profile_lang=lang)
    await sender.edit_text(t('ask_new_name', lang))
    await sender.answer()


@handler(state=ProfileStates.EDIT_NAME)
async def profile_enter_new_name(sender: Sender, state: StateContext):
    async with state.data() as data:
        lang = data.get('profile_lang', sender.lang)
    name = sender.msg.text.strip() if sender.msg.text else ''
    if len(name) < 2:
        await sender.text(t('invalid_name', lang))
        return

    await TelegramUser.objects.filter(telegram_id=sender.user_id).aupdate(full_name=name)
    await state.delete()
    await sender.text(t('name_updated', lang, name=name), markup=main_menu_keyboard(lang))


# ── Edit phone ────────────────────────────────────────────────────────────────

@handler(callback=True, call='profile:edit_phone')
async def profile_edit_phone_start(sender: Sender, state: StateContext):
    lang = sender.lang
    await state.set(ProfileStates.EDIT_PHONE)
    await state.add_data(profile_lang=lang)
    await sender.edit_text(t('ask_new_phone', lang))
    await sender.answer()


@handler(state=ProfileStates.EDIT_PHONE, content_types=['contact', 'text'])
async def profile_enter_new_phone(sender: Sender, state: StateContext):
    async with state.data() as data:
        lang = data.get('profile_lang', sender.lang)
    msg = sender.msg

    phone = None
    if msg.contact and msg.contact.user_id == sender.user_id:
        phone = msg.contact.phone_number
        if phone and not phone.startswith('+'):
            phone = '+' + phone
    elif msg.text:
        text = msg.text.strip()
        if PHONE_RE.match(text):
            phone = text

    if not phone:
        await sender.text(t('invalid_phone', lang), markup=share_phone_keyboard(lang))
        return

    await TelegramUser.objects.filter(telegram_id=sender.user_id).aupdate(phone=phone)
    # Invalidate lang cache since we might refresh user data
    await state.delete()
    await sender.text(t('phone_updated', lang, phone=phone), markup=main_menu_keyboard(lang))


# ── Change language ───────────────────────────────────────────────────────────

@handler(callback=True, call='profile:change_lang')
async def profile_change_lang_start(sender: Sender, state: StateContext):
    lang = sender.lang
    await sender.edit_text(t('select_lang', lang), markup=language_keyboard())
    await sender.answer()


@handler(callback=True, call='lang:uz')
async def profile_lang_uz(sender: Sender, state: StateContext):
    await _apply_lang_change(sender, state, 'uz')


@handler(callback=True, call='lang:ru')
async def profile_lang_ru(sender: Sender, state: StateContext):
    await _apply_lang_change(sender, state, 'ru')


@handler(callback=True, call='lang:uz_kr')
async def profile_lang_uz_kr(sender: Sender, state: StateContext):
    await _apply_lang_change(sender, state, 'uz_kr')


@handler(callback=True, call='lang:en')
async def profile_lang_en(sender: Sender, state: StateContext):
    await _apply_lang_change(sender, state, 'en')


async def _apply_lang_change(sender: Sender, state: StateContext, lang: str):
    current_state = await state.get()
    # Only change lang if NOT in registration flow
    if current_state and 'SELECT_LANGUAGE' in str(current_state):
        return  # handled by start.py

    await set_user_lang(sender.user_id, lang)
    await sender.edit_text(t('lang_changed', lang))
    await sender.text(t('main_menu', lang), markup=main_menu_keyboard(lang))
    await sender.answer()
