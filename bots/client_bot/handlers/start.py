"""
Client bot registration flow:
  /start → language select → name → phone → registered
"""
import logging
import re
from telebot.states.asyncio.context import StateContext

from bots.client_bot.loader import bot, handler
from bots.client_bot.states import RegistrationStates
from bots.client_bot.keyboards.client import (
    language_keyboard, share_phone_keyboard, main_menu_keyboard,
)
from bots.base.sender import Sender
from core.i18n import t, set_user_lang, get_user_lang, LANG_NAMES
from apps.accounts.models import TelegramUser, UserRole, RegisteredVia

logger = logging.getLogger(__name__)
PHONE_RE = re.compile(r'^\+?[0-9]{9,15}$')


# ── /start ────────────────────────────────────────────────────────────────────

@handler(commands=['start'])
async def client_start(sender: Sender, state: StateContext):
    await state.delete()

    # Check if already registered
    try:
        user = await TelegramUser.objects.aget(
            telegram_id=sender.user_id,
            role=UserRole.CLIENT,
            is_active=True,
        )
        lang = user.language or 'uz'
        await sender.text(
            t('registered', lang, name=user.full_name),
            markup=main_menu_keyboard(lang),
        )
        return
    except TelegramUser.DoesNotExist:
        pass

    # New user — start registration
    await state.set(RegistrationStates.SELECT_LANGUAGE)
    await sender.text(t('select_lang', 'uz'), markup=language_keyboard())


# ── Language selection ────────────────────────────────────────────────────────

@handler(callback=True, call='lang:uz', state=RegistrationStates.SELECT_LANGUAGE)
async def select_lang_uz(sender: Sender, state: StateContext):
    await _handle_lang_select(sender, state, 'uz')


@handler(callback=True, call='lang:ru', state=RegistrationStates.SELECT_LANGUAGE)
async def select_lang_ru(sender: Sender, state: StateContext):
    await _handle_lang_select(sender, state, 'ru')


@handler(callback=True, call='lang:uz_kr', state=RegistrationStates.SELECT_LANGUAGE)
async def select_lang_uz_kr(sender: Sender, state: StateContext):
    await _handle_lang_select(sender, state, 'uz_kr')


@handler(callback=True, call='lang:en', state=RegistrationStates.SELECT_LANGUAGE)
async def select_lang_en(sender: Sender, state: StateContext):
    await _handle_lang_select(sender, state, 'en')


async def _handle_lang_select(sender: Sender, state: StateContext, lang: str):
    await state.add_data(selected_lang=lang)
    await state.set(RegistrationStates.ENTER_NAME)
    await sender.edit_text(t('ask_name', lang))
    await sender.answer()


# ── Enter name ────────────────────────────────────────────────────────────────

@handler(state=RegistrationStates.ENTER_NAME, content_types=['text'])
async def client_enter_name(sender: Sender, state: StateContext):
    name = sender.msg.text.strip() if sender.msg.text else ''

    async with state.data() as data:
        lang = data.get('selected_lang', 'uz')

    if len(name) < 2:
        await sender.text(t('invalid_name', lang))
        return

    await state.add_data(**{"reg_name":name})
    await state.set(RegistrationStates.ENTER_PHONE)
    await sender.text(t('ask_phone', lang), markup=share_phone_keyboard(lang))


# ── Enter phone ───────────────────────────────────────────────────────────────

@handler(state=RegistrationStates.ENTER_PHONE, content_types=['contact', 'text'])
async def client_enter_phone(sender: Sender, state: StateContext):
    msg = sender.msg

    async with state.data() as data:
        lang = data.get('selected_lang', 'uz')
        name = data.get('reg_name', '')

    # Extract phone from contact or text
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
        await sender.text(t('invalid_phone', lang))
        return

    # Create user
    tg = msg.from_user
    full_name = name or f"{tg.first_name or ''} {tg.last_name or ''}".strip()

    user, created = await TelegramUser.objects.aupdate_or_create(
        telegram_id=sender.user_id,
        defaults={
            'username': tg.username,
            'full_name': full_name,
            'phone': phone,
            'role': UserRole.CLIENT,
            'language': lang,
            'is_active': True,
            'registered_via': RegisteredVia.CLIENT_BOT,
        },
    )

    await set_user_lang(sender.user_id, lang)
    await state.delete()

    await sender.text(
        t('registered', lang, name=full_name),
        markup=main_menu_keyboard(lang),
    )

    # Notify sales managers about new client
    if created:
        try:
            from bots.main_bot.loader import bot as main_bot
            from core.helpers import notify_sales_managers
            await notify_sales_managers(
                main_bot,
                f"🆕 Yangi mijoz ro'yxatdan o'tdi!\n👤 {full_name}\n📞 {phone}",
            )
        except Exception as exc:
            logger.error("Failed to notify sales about new client: %s", exc)
