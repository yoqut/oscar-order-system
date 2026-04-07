"""
Sales Manager flow:
  Create Order → select agronomist → time slot → client info → confirm → save
"""
import logging
import re
from telebot import types

from bot.loader import bot
from bot.states import SalesStates
from bot.utils.state_manager import StateManager
from bot.utils.helpers import get_or_create_user, notify_user, notify_admins, format_order_card
from bot.keyboards.sales_kb import (
    sales_main_menu, agronomist_list_keyboard,
    time_slot_keyboard, confirm_order_keyboard, cancel_keyboard,
)
from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order, TimeSlot

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r'^\+?[0-9]{9,15}$')


# ── Guards ────────────────────────────────────────────────────────────────────

async def _is_sales(telegram_id: int) -> bool:
    try:
        user = await TelegramUser.objects.aget(telegram_id=telegram_id, is_active=True)
        return user.role == UserRole.SALES_MANAGER
    except TelegramUser.DoesNotExist:
        return False


# ── Entry: main menu button ───────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "📝 Buyurtma yaratish")
async def sales_start_order(message: types.Message):
    if not await _is_sales(message.from_user.id):
        return

    agronomists = [u async for u in TelegramUser.objects.filter(
        role=UserRole.AGRONOMIST, is_active=True
    ).aiterator()]

    if not agronomists:
        await bot.send_message(
            message.chat.id,
            "⚠️ Hozircha aktiv agronom yo'q. Avval admin agronom qo'shishi kerak.",
        )
        return

    await StateManager.set_state(message.from_user.id, SalesStates.SELECT_AGRONOMIST)
    await bot.send_message(
        message.chat.id,
        "🌱 Agronomni tanlang:",
        reply_markup=agronomist_list_keyboard(agronomists),
    )


@bot.message_handler(func=lambda m: m.text == "📋 Mening buyurtmalarim")
async def sales_my_orders(message: types.Message):
    if not await _is_sales(message.from_user.id):
        return

    orders = [o async for o in Order.objects.filter(
        sales_manager__telegram_id=message.from_user.id
    ).order_by('-created_at').aiterator()]

    if not orders:
        await bot.send_message(message.chat.id, "📭 Hali buyurtma yo'q.")
        return

    text = f"📋 <b>Sizning buyurtmalaringiz ({len(orders)} ta):</b>\n\n"
    for order in orders[:20]:
        text += (
            f"• #{order.pk} — {order.client_name} "
            f"[{order.get_status_display()}]\n"
        )
    await bot.send_message(message.chat.id, text)


# ── Step 1: Agronomist selected (callback) ────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("agro_select:"))
async def sales_cb_select_agronomist(call: types.CallbackQuery):
    if not await _is_sales(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    state = await StateManager.get_state(call.from_user.id)
    if state != SalesStates.SELECT_AGRONOMIST:
        await bot.answer_callback_query(call.id)
        return

    agro_id = int(call.data.split(":")[1])
    try:
        agro = await TelegramUser.objects.aget(pk=agro_id, role=UserRole.AGRONOMIST)
    except TelegramUser.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Agronom topilmadi")
        return

    await StateManager.set_state(
        call.from_user.id,
        SalesStates.SELECT_TIME_SLOT,
        data={'agronomist_id': agro_id, 'agronomist_name': agro.full_name},
    )
    await bot.edit_message_text(
        f"✅ Agronom: <b>{agro.full_name}</b>\n\n⏰ Vaqt oralig'ini tanlang:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=time_slot_keyboard(),
    )
    await bot.answer_callback_query(call.id)


# ── Step 2: Time slot selected ────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot:"))
async def sales_cb_select_slot(call: types.CallbackQuery):
    if not await _is_sales(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    state = await StateManager.get_state(call.from_user.id)
    if state != SalesStates.SELECT_TIME_SLOT:
        await bot.answer_callback_query(call.id)
        return

    slot_value = call.data.split(":", 1)[1]
    if slot_value not in TimeSlot.values:
        await bot.answer_callback_query(call.id, "❌ Noto'g'ri vaqt")
        return

    await StateManager.update_data(call.from_user.id, time_slot=slot_value)
    await StateManager.set_state(call.from_user.id, SalesStates.ENTER_CLIENT_NAME)

    slot_label = dict(TimeSlot.choices)[slot_value]
    await bot.edit_message_text(
        f"✅ Vaqt: <b>{slot_label}</b>\n\n👤 Mijozning to'liq ismini kiriting:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=None,
    )
    await bot.send_message(call.message.chat.id, "✍️ To'liq ism:", reply_markup=cancel_keyboard())
    await bot.answer_callback_query(call.id)


# ── Cancel mid-flow ───────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "❌ Bekor qilish")
async def sales_cancel_flow(message: types.Message):
    state = await StateManager.get_state(message.from_user.id)
    if state and state.startswith("sales:"):
        await StateManager.clear(message.from_user.id)
        await bot.send_message(
            message.chat.id,
            "❌ Bekor qilindi.",
            reply_markup=sales_main_menu(),
        )


# ── Step 3-8: Sequential text input ──────────────────────────────────────────

@bot.message_handler(func=lambda m: True, content_types=['text'])
async def sales_text_router(message: types.Message):
    if not await _is_sales(message.from_user.id):
        return

    state, data = await StateManager.get_state_and_data(message.from_user.id)
    if not state or not state.startswith("sales:"):
        return

    text = message.text.strip()
    tid = message.from_user.id

    # ── Client name ──────────────────────────────────────────────────────────
    if state == SalesStates.ENTER_CLIENT_NAME:
        if len(text) < 2:
            await bot.send_message(message.chat.id, "⚠️ Ism juda qisqa. Qayta kiriting:")
            return
        await StateManager.update_data(tid, client_name=text)
        await StateManager.set_state(tid, SalesStates.ENTER_PHONE1)
        await bot.send_message(
            message.chat.id,
            f"✅ Ism: <b>{text}</b>\n\n📞 Birinchi telefon raqamini kiriting:"
        )

    # ── Phone 1 ──────────────────────────────────────────────────────────────
    elif state == SalesStates.ENTER_PHONE1:
        if not PHONE_RE.match(text):
            await bot.send_message(message.chat.id, "⚠️ Noto'g'ri telefon raqami. Qayta kiriting:")
            return
        await StateManager.update_data(tid, phone1=text)
        await StateManager.set_state(tid, SalesStates.ENTER_PHONE2)
        await bot.send_message(
            message.chat.id,
            f"✅ Tel 1: <b>{text}</b>\n\n📞 Ikkinchi telefon (yoki /skip):"
        )

    # ── Phone 2 ──────────────────────────────────────────────────────────────
    elif state == SalesStates.ENTER_PHONE2:
        phone2 = None
        if text.lower() not in ('/skip', 'skip', '-'):
            if not PHONE_RE.match(text):
                await bot.send_message(message.chat.id, "⚠️ Noto'g'ri telefon raqami. /skip yozing o'tkazib yuborish uchun:")
                return
            phone2 = text
        await StateManager.update_data(tid, phone2=phone2)
        await StateManager.set_state(tid, SalesStates.ENTER_TREE_COUNT)
        await bot.send_message(message.chat.id, "🌳 Daraxt sonini kiriting (raqam):")

    # ── Tree count ────────────────────────────────────────────────────────────
    elif state == SalesStates.ENTER_TREE_COUNT:
        if not text.isdigit() or int(text) < 1:
            await bot.send_message(message.chat.id, "⚠️ Faqat musbat son kiriting:")
            return
        await StateManager.update_data(tid, tree_count=int(text))
        await StateManager.set_state(tid, SalesStates.ENTER_PROBLEM)
        await bot.send_message(message.chat.id, "🔴 Asosiy muammo/dardni yozing:")

    # ── Problem ───────────────────────────────────────────────────────────────
    elif state == SalesStates.ENTER_PROBLEM:
        if len(text) < 5:
            await bot.send_message(message.chat.id, "⚠️ Muammoani batafsil yozing:")
            return
        await StateManager.update_data(tid, problem=text)
        await StateManager.set_state(tid, SalesStates.ENTER_ADDRESS)
        await bot.send_message(message.chat.id, "📍 Manzilni kiriting:")

    # ── Address ───────────────────────────────────────────────────────────────
    elif state == SalesStates.ENTER_ADDRESS:
        if len(text) < 5:
            await bot.send_message(message.chat.id, "⚠️ Manzilni to'liqroq yozing:")
            return
        await StateManager.update_data(tid, address=text)
        await StateManager.set_state(tid, SalesStates.CONFIRM_ORDER)

        data = await StateManager.get_data(tid)
        slot_label = dict(TimeSlot.choices).get(data.get('time_slot', ''), '')
        summary = (
            f"📋 <b>Buyurtma ma'lumotlari:</b>\n\n"
            f"👤 Mijoz: {data.get('client_name')}\n"
            f"📞 Tel 1: {data.get('phone1')}\n"
            f"📞 Tel 2: {data.get('phone2') or '—'}\n"
            f"🌳 Daraxtlar: {data.get('tree_count')}\n"
            f"⏰ Vaqt: {slot_label}\n"
            f"🔴 Muammo: {data.get('problem')}\n"
            f"📍 Manzil: {text}\n"
            f"🌱 Agronom: {data.get('agronomist_name')}"
        )
        await bot.send_message(
            message.chat.id,
            summary,
            reply_markup=confirm_order_keyboard(),
        )


# ── Step 9: Confirmation callback ─────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("order_confirm:"))
async def sales_cb_confirm_order(call: types.CallbackQuery):
    if not await _is_sales(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    state = await StateManager.get_state(call.from_user.id)
    if state != SalesStates.CONFIRM_ORDER:
        await bot.answer_callback_query(call.id)
        return

    answer = call.data.split(":")[1]
    if answer == "no":
        await StateManager.clear(call.from_user.id)
        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        await bot.send_message(call.message.chat.id, "❌ Bekor qilindi.", reply_markup=sales_main_menu())
        await bot.answer_callback_query(call.id)
        return

    data = await StateManager.get_data(call.from_user.id)

    try:
        sales_user = await TelegramUser.objects.aget(telegram_id=call.from_user.id)
        agro = await TelegramUser.objects.aget(pk=data['agronomist_id'])

        order = await Order.objects.acreate(
            sales_manager=sales_user,
            agronomist=agro,
            client_name=data['client_name'],
            phone1=data['phone1'],
            phone2=data.get('phone2') or '',
            tree_count=data['tree_count'],
            problem=data['problem'],
            address=data['address'],
            time_slot=data['time_slot'],
        )
    except Exception as exc:
        logger.error("Order creation failed: %s", exc)
        await bot.send_message(call.message.chat.id, "❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
        await bot.answer_callback_query(call.id)
        return

    await StateManager.clear(call.from_user.id)
    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    await bot.send_message(
        call.message.chat.id,
        f"✅ Buyurtma #{order.pk} yaratildi!",
        reply_markup=sales_main_menu(),
    )

    # Notify agronomist
    from bot.keyboards.agronomist_kb import order_actions_keyboard
    agro_text = (
        f"🆕 <b>Yangi buyurtma #{order.pk}</b>\n\n"
        + format_order_card(order)
    )
    await notify_user(
        bot, agro.telegram_id, agro_text,
        reply_markup=order_actions_keyboard(order.pk)
    )

    # Notify admins
    admin_text = (
        f"🆕 <b>Yangi buyurtma #{order.pk}</b> yaratildi.\n"
        f"Sotuvchi: {sales_user.full_name}\n\n"
        + format_order_card(order)
    )
    from bot.keyboards.admin_kb import approve_order_keyboard
    await notify_admins(bot, admin_text, reply_markup=approve_order_keyboard(order.pk))

    await bot.answer_callback_query(call.id, f"✅ Buyurtma #{order.pk} yaratildi!")
