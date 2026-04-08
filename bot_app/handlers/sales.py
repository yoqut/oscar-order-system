"""
Sales Manager flow:
  Create Order → select agronomist → time slot → client info → confirm → save
"""
import logging
import re
from telebot import types
from telebot.states.asyncio.context import StateContext

from ..core.loader import bot
from ..core.use_states import SalesStates
from ..core.callback_factories import slot_factory, order_confirm_factory
from ..utils.helpers import notify_user, notify_admins, format_order_card
from ..keyboards.sales_kb import (
    sales_main_menu, confirm_order_keyboard, cancel_keyboard,
)
from apps.accounts.models import TelegramUser
from apps.orders.models import Order, TimeSlot

logger = logging.getLogger(__name__)


PHONE_RE = re.compile(r'^\+?[0-9]{9,15}$')

# ── Cancel mid-flow ───────────────────────────────────────────────────────────

@bot.message_handler(text=["❌ Bekor qilish"], state=[
    SalesStates.SELECT_AGRONOMIST, SalesStates.SELECT_TIME_SLOT,
    SalesStates.ENTER_CLIENT_NAME, SalesStates.ENTER_PHONE1,
    SalesStates.ENTER_PHONE2, SalesStates.ENTER_TREE_COUNT,
    SalesStates.ENTER_PROBLEM, SalesStates.ENTER_ADDRESS,
    SalesStates.CONFIRM_ORDER,
])
async def sales_cancel_flow(message: types.Message, state: StateContext):
    await state.delete()
    await bot.send_message(
        message.chat.id,
        "❌ Bekor qilindi.",
        reply_markup=sales_main_menu(),
    )

# ── Step 1: Agronomist selected ───────────────────────────────────────────────



# ── Step 2: Time slot selected ────────────────────────────────────────────────

@bot.callback_query_handler(func=None, config=slot_factory.filter(),
                             state=SalesStates.SELECT_TIME_SLOT)
async def sales_cb_select_slot(call: types.CallbackQuery, state: StateContext):
    cb = slot_factory.parse(call.data)
    # cb['slot'] is the list index (str) — decode back to the actual TimeSlot value
    slot_choices = list(TimeSlot.choices)
    try:
        slot_idx = int(cb['slot'])
        slot_value, slot_label = slot_choices[slot_idx]
    except (ValueError, IndexError):
        await bot.answer_callback_query(call.id, "❌ Noto'g'ri vaqt")
        return
    await state.add_data(time_slot=slot_value)
    await state.set(SalesStates.ENTER_CLIENT_NAME)
    await bot.edit_message_text(
        f"✅ Vaqt: <b>{slot_label}</b>",
        call.message.chat.id,
        call.message.message_id,
    )
    await bot.send_message(
        call.message.chat.id,
        "👤 Mijozning to'liq ismini kiriting:",
        reply_markup=cancel_keyboard(),
    )
    await bot.answer_callback_query(call.id)


# ── Step 3: Client name ───────────────────────────────────────────────────────

@bot.message_handler(state=SalesStates.ENTER_CLIENT_NAME)
async def sales_enter_client_name(message: types.Message, state: StateContext):
    text = message.text.strip()
    if len(text) < 2:
        await bot.send_message(message.chat.id, "⚠️ Ism juda qisqa. Qayta kiriting:")
        return
    await state.add_data(client_name=text)
    await state.set(SalesStates.ENTER_PHONE1)
    await bot.send_message(message.chat.id, f"✅ Ism: <b>{text}</b>\n\n📞 Birinchi telefon raqamini kiriting:")


# ── Step 4: Phone 1 ───────────────────────────────────────────────────────────

@bot.message_handler(state=SalesStates.ENTER_PHONE1)
async def sales_enter_phone1(message: types.Message, state: StateContext):
    text = message.text.strip()
    if not PHONE_RE.match(text):
        await bot.send_message(message.chat.id, "⚠️ Noto'g'ri telefon raqami. Qayta kiriting:")
        return
    await state.add_data(phone1=text)
    await state.set(SalesStates.ENTER_PHONE2)
    await bot.send_message(
        message.chat.id,
        f"✅ Tel 1: <b>{text}</b>\n\n📞 Ikkinchi telefon (yoki /skip):",
    )


# ── Step 5: Phone 2 ───────────────────────────────────────────────────────────

@bot.message_handler(state=SalesStates.ENTER_PHONE2)
async def sales_enter_phone2(message: types.Message, state: StateContext):
    text = message.text.strip()
    phone2 = None
    if text.lower() not in ('/skip', 'skip', '-'):
        if not PHONE_RE.match(text):
            await bot.send_message(
                message.chat.id,
                "⚠️ Noto'g'ri telefon raqami. /skip yozing o'tkazib yuborish uchun:",
            )
            return
        phone2 = text
    await state.add_data(phone2=phone2)
    await state.set(SalesStates.ENTER_TREE_COUNT)
    await bot.send_message(message.chat.id, "🌳 Daraxt sonini kiriting (raqam):")


# ── Step 6: Tree count ────────────────────────────────────────────────────────

@bot.message_handler(state=SalesStates.ENTER_TREE_COUNT, is_digit=True)
async def sales_enter_tree_count(message: types.Message, state: StateContext):
    count = int(message.text.strip())
    if count < 1:
        await bot.send_message(message.chat.id, "⚠️ Faqat musbat son kiriting:")
        return
    await state.add_data(tree_count=count)
    await state.set(SalesStates.ENTER_PROBLEM)
    await bot.send_message(message.chat.id, "🔴 Asosiy muammo/dardni yozing:")


@bot.message_handler(state=SalesStates.ENTER_TREE_COUNT, is_digit=False)
async def sales_enter_tree_count_invalid(message: types.Message):
    await bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting:")


# ── Step 7: Problem ───────────────────────────────────────────────────────────

@bot.message_handler(state=SalesStates.ENTER_PROBLEM)
async def sales_enter_problem(message: types.Message, state: StateContext):
    text = message.text.strip()
    if len(text) < 5:
        await bot.send_message(message.chat.id, "⚠️ Muammoani batafsil yozing:")
        return
    await state.add_data(problem=text)
    await state.set(SalesStates.ENTER_ADDRESS)
    await bot.send_message(message.chat.id, "📍 Manzilni kiriting:")


# ── Step 8: Address ───────────────────────────────────────────────────────────

@bot.message_handler(state=SalesStates.ENTER_ADDRESS)
async def sales_enter_address(message: types.Message, state: StateContext):
    text = message.text.strip()
    if len(text) < 5:
        await bot.send_message(message.chat.id, "⚠️ Manzilni to'liqroq yozing:")
        return

    await state.add_data(address=text)
    await state.set(SalesStates.CONFIRM_ORDER)

    async with state.data() as data:
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


# ── Step 9: Confirm ───────────────────────────────────────────────────────────

@bot.callback_query_handler(func=None, config=order_confirm_factory.filter(),
                             state=SalesStates.CONFIRM_ORDER)
async def sales_cb_confirm_order(call: types.CallbackQuery, state: StateContext):
    cb = order_confirm_factory.parse(call.data)

    if cb['answer'] == 'no':
        await state.delete()
        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        await bot.send_message(call.message.chat.id, "❌ Bekor qilindi.", reply_markup=sales_main_menu())
        await bot.answer_callback_query(call.id)
        return

    async with state.data() as data:
        agronomist_id = data['agronomist_id']
        client_name = data['client_name']
        phone1 = data['phone1']
        phone2 = data.get('phone2') or ''
        tree_count = data['tree_count']
        problem = data['problem']
        address = data['address']
        time_slot = data['time_slot']

    try:
        sales_user = await TelegramUser.objects.aget(telegram_id=call.from_user.id)
        agro = await TelegramUser.objects.aget(pk=agronomist_id)
        order = await Order.objects.acreate(
            sales_manager=sales_user,
            agronomist=agro,
            client_name=client_name,
            phone1=phone1,
            phone2=phone2,
            tree_count=tree_count,
            problem=problem,
            address=address,
            time_slot=time_slot,
        )
    except Exception as exc:
        logger.error("Order creation failed: %s", exc)
        await bot.send_message(call.message.chat.id, "❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
        await bot.answer_callback_query(call.id)
        return

    await state.delete()
    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    await bot.send_message(
        call.message.chat.id,
        f"✅ Buyurtma #{order.pk} yaratildi!",
        reply_markup=sales_main_menu(),
    )

    from bot_app.keyboards.agronomist_kb import order_actions_keyboard
    await notify_user(
        bot, agro.telegram_id,
        f"🆕 <b>Yangi buyurtma #{order.pk}</b>\n\n" + format_order_card(order),
        reply_markup=order_actions_keyboard(order.pk),
    )

    from bot_app.keyboards.admin_kb import approve_order_keyboard
    await notify_admins(
        bot,
        f"🆕 <b>Yangi buyurtma #{order.pk}</b> yaratildi.\n"
        f"Sotuvchi: {sales_user.full_name}\n\n" + format_order_card(order),
        reply_markup=approve_order_keyboard(order.pk),
    )

    await bot.answer_callback_query(call.id, f"✅ Buyurtma #{order.pk} yaratildi!")
