"""
Agronomist flow:
  View orders → accept/cancel → complete service (treatment details + proof upload)
"""
import logging
from datetime import datetime
from telebot import types
from telebot.states.asyncio.context import StateContext

from ..core.loader import bot
from ..core.use_states import AgronomistStates
from ..core.callback_factories import (
    agro_view_factory, agro_cancel_factory, agro_complete_factory,
    agro_page_factory, root_factory, payment_factory, retreatment_factory,
)
from ..utils.helpers import notify_user, notify_admins, format_order_card
from ..keyboards.agronomist_kb import (
    agronomist_main_menu, order_actions_keyboard, orders_list_keyboard,
    root_treatment_keyboard, payment_type_keyboard,
    retreatment_keyboard, cancel_keyboard,
)
from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order, OrderStatus, TreatmentDetails

logger = logging.getLogger(__name__)


async def _is_agro(telegram_id: int) -> bool:
    try:
        user = await TelegramUser.objects.aget(telegram_id=telegram_id, is_active=True)
        return user.role == UserRole.AGRONOMIST
    except TelegramUser.DoesNotExist:
        return False


# ── My Orders ─────────────────────────────────────────────────────────────────

@bot.message_handler(text=["📋 Mening buyurtmalarim", "🔄 Faol buyurtmalar"])
async def agro_my_orders(message: types.Message):
    if not await _is_agro(message.from_user.id):
        return

    orders = [o async for o in Order.objects.filter(
        agronomist__telegram_id=message.from_user.id,
        status__in=[OrderStatus.APPROVED, OrderStatus.IN_PROGRESS, OrderStatus.PENDING],
    ).order_by('-created_at').aiterator()]

    if not orders:
        await bot.send_message(message.chat.id, "📭 Faol buyurtmalar yo'q.")
        return

    await bot.send_message(
        message.chat.id,
        f"📋 <b>Buyurtmalaringiz ({len(orders)} ta):</b>",
        reply_markup=orders_list_keyboard(orders),
    )


# ── Cancel mid-flow ───────────────────────────────────────────────────────────

@bot.message_handler(text=["❌ Bekor qilish"], state=[
    AgronomistStates.ENTER_CANCEL_REASON, AgronomistStates.ENTER_TREATMENT_COUNT,
    AgronomistStates.ENTER_ROOT_TREATMENT, AgronomistStates.ENTER_FINAL_PRICE,
    AgronomistStates.SELECT_PAYMENT_TYPE, AgronomistStates.SELECT_RETREATMENT,
    AgronomistStates.ENTER_RETREATMENT_DATE, AgronomistStates.UPLOAD_PROOF,
])
async def agro_cancel_flow(message: types.Message, state: StateContext):
    await state.delete()
    await bot.send_message(
        message.chat.id,
        "❌ Bekor qilindi.",
        reply_markup=agronomist_main_menu(),
    )


# ── View single order ─────────────────────────────────────────────────────────

@bot.callback_query_handler(func=None, config=agro_view_factory.filter())
async def agro_cb_view_order(call: types.CallbackQuery):
    if not await _is_agro(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    cb = agro_view_factory.parse(call.data)
    order_id = int(cb['order_id'])
    try:
        order = await Order.objects.select_related('sales_manager').aget(
            pk=order_id, agronomist__telegram_id=call.from_user.id,
        )
    except Order.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Buyurtma topilmadi")
        return

    text = format_order_card(order) + f"\n\n👨‍💼 Sotuvchi: {order.sales_manager.full_name}"
    await bot.send_message(call.message.chat.id, text, reply_markup=order_actions_keyboard(order.pk))
    await bot.answer_callback_query(call.id)


# ── Pagination ────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=None, config=agro_page_factory.filter())
async def agro_cb_page(call: types.CallbackQuery):
    if not await _is_agro(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    cb = agro_page_factory.parse(call.data)
    page = int(cb['page'])
    orders = [o async for o in Order.objects.filter(
        agronomist__telegram_id=call.from_user.id,
        status__in=[OrderStatus.APPROVED, OrderStatus.IN_PROGRESS, OrderStatus.PENDING],
    ).order_by('-created_at').aiterator()]

    await bot.edit_message_reply_markup(
        call.message.chat.id, call.message.message_id,
        reply_markup=orders_list_keyboard(orders, page=page),
    )
    await bot.answer_callback_query(call.id)


# ── Cancel order — sets state ─────────────────────────────────────────────────

@bot.callback_query_handler(func=None, config=agro_cancel_factory.filter())
async def agro_cb_cancel_order(call: types.CallbackQuery, state: StateContext):
    if not await _is_agro(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    cb = agro_cancel_factory.parse(call.data)
    order_id = int(cb['order_id'])
    await state.set(AgronomistStates.ENTER_CANCEL_REASON)
    await state.add_data(order_id=order_id)
    await bot.send_message(
        call.message.chat.id,
        f"❌ Buyurtma #{order_id} uchun bekor qilish sababini yozing:",
        reply_markup=cancel_keyboard(),
    )
    await bot.answer_callback_query(call.id)


# ── Cancel reason text ────────────────────────────────────────────────────────

@bot.message_handler(state=AgronomistStates.ENTER_CANCEL_REASON)
async def agro_enter_cancel_reason(message: types.Message, state: StateContext):
    async with state.data() as data:
        order_id = data.get('order_id')

    try:
        order = await Order.objects.select_related('client', 'sales_manager').aget(
            pk=order_id, agronomist__telegram_id=message.from_user.id,
        )
    except Order.DoesNotExist:
        await state.delete()
        await bot.send_message(message.chat.id, "❌ Buyurtma topilmadi.", reply_markup=agronomist_main_menu())
        return

    order.status = OrderStatus.CANCELLED
    order.cancel_reason = message.text.strip()
    await order.asave(update_fields=['status', 'cancel_reason', 'updated_at'])
    await state.delete()

    await bot.send_message(
        message.chat.id,
        f"✅ Buyurtma #{order_id} bekor qilindi.",
        reply_markup=agronomist_main_menu(),
    )

    if order.client:
        await notify_user(
            bot, order.client.telegram_id,
            f"❌ Buyurtma #{order_id} bekor qilindi.\nSabab: {message.text.strip()}",
        )

    agro = await TelegramUser.objects.aget(telegram_id=message.from_user.id)
    cancel_text = (
        f"❌ <b>Buyurtma #{order_id} bekor qilindi</b>\n"
        f"Agronom: {agro.full_name}\nSabab: {message.text.strip()}"
    )
    await notify_admins(bot, cancel_text)
    await notify_user(bot, order.sales_manager.telegram_id, cancel_text)


# ── Complete order — entry point ──────────────────────────────────────────────

@bot.callback_query_handler(func=None, config=agro_complete_factory.filter())
async def agro_cb_complete_order(call: types.CallbackQuery, state: StateContext):
    if not await _is_agro(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    cb = agro_complete_factory.parse(call.data)
    order_id = int(cb['order_id'])
    try:
        order = await Order.objects.aget(pk=order_id, agronomist__telegram_id=call.from_user.id)
    except Order.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Buyurtma topilmadi")
        return

    if order.status not in (OrderStatus.APPROVED, OrderStatus.IN_PROGRESS, OrderStatus.PENDING):
        await bot.answer_callback_query(call.id, "⚠️ Bu buyurtma allaqachon yakunlangan yoki bekor qilingan")
        return

    await state.set(AgronomistStates.ENTER_TREATMENT_COUNT)
    await state.add_data(order_id=order_id)
    await bot.send_message(
        call.message.chat.id,
        f"✅ Buyurtma #{order_id} yakunlash jarayoni boshlandi.\n\n"
        f"🔢 Nechta ishlov berildi? (raqam kiriting):",
        reply_markup=cancel_keyboard(),
    )
    await bot.answer_callback_query(call.id)


# ── Treatment count ───────────────────────────────────────────────────────────

@bot.message_handler(state=AgronomistStates.ENTER_TREATMENT_COUNT, is_digit=True)
async def agro_enter_treatment_count(message: types.Message, state: StateContext):
    count = int(message.text.strip())
    if count < 1:
        await bot.send_message(message.chat.id, "⚠️ Faqat musbat son kiriting:")
        return
    await state.add_data(treatment_count=count)
    await state.set(AgronomistStates.ENTER_ROOT_TREATMENT)
    await bot.send_message(
        message.chat.id,
        "🌿 Ildizga ishlov berildi?",
        reply_markup=root_treatment_keyboard(),
    )


@bot.message_handler(state=AgronomistStates.ENTER_TREATMENT_COUNT, is_digit=False)
async def agro_enter_treatment_count_invalid(message: types.Message):
    await bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting:")


# ── Root treatment (inline) ───────────────────────────────────────────────────

@bot.callback_query_handler(func=None, config=root_factory.filter(),
                             state=AgronomistStates.ENTER_ROOT_TREATMENT)
async def agro_cb_root_treatment(call: types.CallbackQuery, state: StateContext):
    cb = root_factory.parse(call.data)
    root_applied = cb['value'] == 'yes'
    label = "Ha ✅" if root_applied else "Yo'q ❌"

    await state.add_data(root_treatment_applied=root_applied)
    await state.set(AgronomistStates.ENTER_FINAL_PRICE)
    await bot.edit_message_text(
        f"✅ Ildiz ishlov: <b>{label}</b>\n\n💰 Kelishilgan yakuniy narxni kiriting (so'mda):",
        call.message.chat.id,
        call.message.message_id,
    )
    await bot.answer_callback_query(call.id)


# ── Final price ───────────────────────────────────────────────────────────────

@bot.message_handler(state=AgronomistStates.ENTER_FINAL_PRICE)
async def agro_enter_final_price(message: types.Message, state: StateContext):
    price_str = message.text.strip().replace(',', '.').replace(' ', '')
    try:
        price = float(price_str)
        if price < 0:
            raise ValueError
    except ValueError:
        await bot.send_message(message.chat.id, "⚠️ To'g'ri narx kiriting (masalan: 150000):")
        return

    await state.add_data(final_price=price_str)
    await state.set(AgronomistStates.SELECT_PAYMENT_TYPE)
    await bot.send_message(
        message.chat.id,
        f"✅ Narx: <b>{price:,.0f} so'm</b>\n\n💳 To'lov turini tanlang:",
        reply_markup=payment_type_keyboard(),
    )


# ── Payment type (inline) ─────────────────────────────────────────────────────

@bot.callback_query_handler(func=None, config=payment_factory.filter(),
                             state=AgronomistStates.SELECT_PAYMENT_TYPE)
async def agro_cb_payment_type(call: types.CallbackQuery, state: StateContext):
    cb = payment_factory.parse(call.data)
    payment_type = cb['ptype']
    labels = {'cash': 'Naqd pul 💵', 'card': 'Karta 💳', 'bank_transfer': "Bank o'tkazmasi 🏦"}
    label = labels.get(payment_type, payment_type)

    await state.add_data(payment_type=payment_type)
    await state.set(AgronomistStates.SELECT_RETREATMENT)
    await bot.edit_message_text(
        f"✅ To'lov: <b>{label}</b>\n\n🔁 Qayta ishlov kerakmi?",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=retreatment_keyboard(),
    )
    await bot.answer_callback_query(call.id)


# ── Re-treatment (inline) ─────────────────────────────────────────────────────

@bot.callback_query_handler(func=None, config=retreatment_factory.filter(),
                             state=AgronomistStates.SELECT_RETREATMENT)
async def agro_cb_retreatment(call: types.CallbackQuery, state: StateContext):
    cb = retreatment_factory.parse(call.data)
    needed = cb['value'] == 'yes'
    await state.add_data(re_treatment_needed=needed)

    if needed:
        await state.set(AgronomistStates.ENTER_RETREATMENT_DATE)
        await bot.edit_message_text(
            "📅 Qayta ishlov sanasini kiriting (KK.OO.YYYY):",
            call.message.chat.id,
            call.message.message_id,
        )
    else:
        await state.set(AgronomistStates.UPLOAD_PROOF)
        await bot.edit_message_text(
            "📸 Ish isbotnomasi uchun foto yoki video yuboring:",
            call.message.chat.id,
            call.message.message_id,
        )
    await bot.answer_callback_query(call.id)


# ── Re-treatment date ─────────────────────────────────────────────────────────

@bot.message_handler(state=AgronomistStates.ENTER_RETREATMENT_DATE)
async def agro_enter_retreatment_date(message: types.Message, state: StateContext):
    try:
        dt = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await bot.send_message(
            message.chat.id,
            "⚠️ Sana formati: KK.OO.YYYY (masalan: 25.04.2024):",
        )
        return

    await state.add_data(re_treatment_date=str(dt))
    await state.set(AgronomistStates.UPLOAD_PROOF)
    await bot.send_message(
        message.chat.id,
        f"✅ Qayta ishlov sanasi: <b>{dt}</b>\n\n📸 Ish isbotnomasi uchun foto yoki video yuboring:",
    )


# ── Proof upload — finalize order ─────────────────────────────────────────────

@bot.message_handler(state=AgronomistStates.UPLOAD_PROOF, content_types=['photo', 'video'])
async def agro_proof_upload(message: types.Message, state: StateContext):
    async with state.data() as data:
        order_id = data.get('order_id')
        treatment_count = data.get('treatment_count')
        root_treatment_applied = data.get('root_treatment_applied', False)
        final_price = data.get('final_price')
        payment_type = data.get('payment_type')
        re_treatment_needed = data.get('re_treatment_needed', False)
        re_treatment_date_str = data.get('re_treatment_date')

    if not order_id:
        await bot.send_message(message.chat.id, "❌ Xatolik: buyurtma ID topilmadi.")
        await state.delete()
        return

    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'
    else:
        file_id = message.video.file_id
        file_type = 'video'

    try:
        order = await Order.objects.select_related(
            'client', 'sales_manager', 'agronomist'
        ).aget(pk=order_id)

        re_date = None
        if re_treatment_date_str:
            re_date = datetime.strptime(re_treatment_date_str, "%Y-%m-%d").date()

        details = await TreatmentDetails.objects.acreate(
            order=order,
            treatment_count=treatment_count,
            root_treatment_applied=root_treatment_applied,
            final_price=final_price,
            payment_type=payment_type,
            re_treatment_needed=re_treatment_needed,
            re_treatment_date=re_date,
            proof_file_id=file_id,
            proof_file_type=file_type,
        )
        order.status = OrderStatus.COMPLETED
        await order.asave(update_fields=['status', 'updated_at'])

    except Exception as exc:
        logger.error("Failed to save treatment details: %s", exc)
        await bot.send_message(message.chat.id, "❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
        return

    await state.delete()
    await bot.send_message(
        message.chat.id,
        f"✅ <b>Buyurtma #{order_id} yakunlandi!</b>\nMa'lumotlar saqlandi.",
        reply_markup=agronomist_main_menu(),
    )

    if order.client:
        from bot_app.keyboards.client_kb import client_service_done_keyboard
        await notify_user(
            bot, order.client.telegram_id,
            f"✅ <b>Xizmat bajarildi!</b>\n\n"
            f"Order #{order_id} bo'yicha ishlov yakunlandi.\n"
            f"Iltimos, xizmatni tasdiqlang yoki rad eting:",
            reply_markup=client_service_done_keyboard(order_id),
        )

    summary = (
        f"✅ <b>Buyurtma #{order_id} yakunlandi</b>\n"
        f"Mijoz: {order.client_name}\n" + details.get_summary()
    )
    await notify_user(bot, order.sales_manager.telegram_id, summary)
    await notify_admins(bot, summary)
