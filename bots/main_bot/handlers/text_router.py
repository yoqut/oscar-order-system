"""
Main bot catch-all text router.
Handles admin text input states (broadcast, messaging, user management).
MUST be imported last.
"""
import logging
from telebot.states.asyncio.context import StateContext

from bots.main_bot.loader import bot, handler
from bots.main_bot.states import AdminStates
from bots.main_bot.keyboards.admin import admin_main_menu, confirm_broadcast_keyboard
from bots.base.sender import Sender
from core.helpers import notify_user
from apps.accounts.models import TelegramUser, UserRole, RegisteredVia

logger = logging.getLogger(__name__)


@handler(is_admin=True, state=AdminStates.ADD_MANAGER_ID)
async def admin_enter_manager_id(sender: Sender, state: StateContext):
    text = sender.msg.text.strip()
    if not text.isdigit():
        await sender.text("⚠️ Faqat raqam kiriting (Telegram ID):")
        return
    await state.add_data(new_user_tg_id=int(text))
    await state.set(AdminStates.ADD_MANAGER_NAME)
    await sender.text("👤 Sotuvchining to'liq ismini kiriting:")


@handler(is_admin=True, state=AdminStates.ADD_MANAGER_NAME)
async def admin_enter_manager_name(sender: Sender, state: StateContext):
    name = sender.msg.text.strip()
    if len(name) < 2:
        await sender.text("⚠️ Ism juda qisqa. Qayta kiriting:")
        return

    async with state.data() as data:
        tg_id = data.get('new_user_tg_id')

    if not tg_id:
        await state.delete()
        await sender.text("❌ Xatolik.", markup=admin_main_menu())
        return

    user, created = await TelegramUser.objects.aupdate_or_create(
        telegram_id=tg_id,
        defaults={
            'full_name': name,
            'role': UserRole.SALES_MANAGER,
            'is_active': True,
            'registered_via': RegisteredVia.ADMIN,
        },
    )
    await state.delete()
    action = "qo'shildi" if created else "yangilandi"
    await sender.text(
        f"✅ Sotuvchi {action}: <b>{name}</b> (ID: {tg_id})",
        markup=admin_main_menu(),
    )
    await notify_user(
        bot, tg_id,
        f"✅ Siz sotuvchi sifatida qo'shildingiz!\nIsm: {name}\nBotda /start bosing."
    )


@handler(is_admin=True, state=AdminStates.ADD_AGRONOMIST_ID)
async def admin_enter_agronomist_id(sender: Sender, state: StateContext):
    text = sender.msg.text.strip()
    if not text.isdigit():
        await sender.text("⚠️ Faqat raqam kiriting (Telegram ID):")
        return
    await state.add_data(new_user_tg_id=int(text))
    await state.set(AdminStates.ADD_AGRONOMIST_NAME)
    await sender.text("👤 Agronomning to'liq ismini kiriting:")


@handler(is_admin=True, state=AdminStates.ADD_AGRONOMIST_NAME)
async def admin_enter_agronomist_name(sender: Sender, state: StateContext):
    name = sender.msg.text.strip()
    if len(name) < 2:
        await sender.text("⚠️ Ism juda qisqa. Qayta kiriting:")
        return

    async with state.data() as data:
        tg_id = data.get('new_user_tg_id')

    if not tg_id:
        await state.delete()
        await sender.text("❌ Xatolik.", markup=admin_main_menu())
        return

    user, created = await TelegramUser.objects.aupdate_or_create(
        telegram_id=tg_id,
        defaults={
            'full_name': name,
            'role': UserRole.AGRONOMIST,
            'is_active': True,
            'registered_via': RegisteredVia.ADMIN,
        },
    )
    await state.delete()
    action = "qo'shildi" if created else "yangilandi"
    await sender.text(
        f"✅ Agronom {action}: <b>{name}</b> (ID: {tg_id})",
        markup=admin_main_menu(),
    )
    await notify_user(
        bot, tg_id,
        f"✅ Siz agronom sifatida qo'shildingiz!\nIsm: {name}\nBotda /start bosing."
    )


@handler(is_admin=True, state=AdminStates.SEND_MESSAGE_SELECT_USER)
async def admin_msg_user_enter_id(sender: Sender, state: StateContext):
    text = sender.msg.text.strip()
    if not text.isdigit():
        await sender.text("⚠️ Faqat raqam kiriting (Telegram ID):")
        return
    await state.add_data(target_tg_id=int(text))
    await state.set(AdminStates.SEND_MESSAGE_TEXT)
    await sender.text("📝 Xabar matnini kiriting:")


@handler(is_admin=True, state=AdminStates.SEND_MESSAGE_TEXT)
async def admin_msg_user_enter_text(sender: Sender, state: StateContext):
    text = sender.msg.text.strip()

    async with state.data() as data:
        target_id = data.get('target_tg_id')

    if not target_id:
        await state.delete()
        await sender.text("❌ Xatolik.", markup=admin_main_menu())
        return

    await state.delete()
    success = await notify_user(bot, target_id, text)
    status = f"✅ ID {target_id} ga yuborildi." if success else f"❌ ID {target_id} ga yuborib bo'lmadi."
    await sender.text(status, markup=admin_main_menu())


@handler(is_admin=True, state=AdminStates.BROADCAST_TEXT)
async def admin_broadcast_enter_text(sender: Sender, state: StateContext):
    text = sender.msg.text.strip()
    if len(text) < 3:
        await sender.text("⚠️ Xabar juda qisqa:")
        return
    await state.add_data(broadcast_text=text)
    await state.set(AdminStates.CONFIRM_BROADCAST)
    await sender.text(
        f"📢 <b>Barcha foydalanuvchilarga yuboriladigan xabar:</b>\n\n{text}\n\nTasdiqlaysizmi?",
        markup=confirm_broadcast_keyboard(),
    )


# ── Default catch-all (must be last) ─────────────────────────────────────────

@handler(is_staff=True, func=lambda m: True)
async def staff_unknown_command(sender: Sender, state: StateContext):
    current_state = await state.get()
    if current_state:
        return  # Let specific state handlers deal with it
    await sender.text("❓ Noma'lum buyruq. Menyu tugmalaridan foydalaning.")
