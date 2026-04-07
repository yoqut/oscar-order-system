"""
Agronomist flow:
  View orders → accept/cancel → complete service (treatment details + proof upload)
"""
import logging
from datetime import datetime
from telebot import types

from bot.loader import bot
from bot.states import AgronomistStates
from bot.utils.state_manager import StateManager
from bot.utils.helpers import get_or_create_user, notify_user, notify_admins, format_order_card
from bot.keyboards.agronomist_kb import (
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

@bot.message_handler(func=lambda m: m.text == "📋 Mening buyurtmalarim")
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


@bot.message_handler(func=lambda m: m.text == "🔄 Faol buyurtmalar")
async def agro_active_orders(message: types.Message):
    if not await _is_agro(message.from_user.id):
        return
    await agro_my_orders(message)


# ── View single order ─────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("agro:view:"))
async def agro_cb_view_order(call: types.CallbackQuery):
    if not await _is_agro(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    order_id = int(call.data.split(":")[2])
    try:
        order = await Order.objects.select_related('sales_manager').aget(
            pk=order_id, agronomist__telegram_id=call.from_user.id
        )
    except Order.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Buyurtma topilmadi")
        return

    text = format_order_card(order)
    text += f"\n\n👨‍💼 Sotuvchi: {order.sales_manager.full_name}"

    await bot.send_message(
        call.message.chat.id,
        text,
        reply_markup=order_actions_keyboard(order.pk),
    )
    await bot.answer_callback_query(call.id)


# ── Pagination ────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("agro:page:"))
async def agro_cb_page(call: types.CallbackQuery):
    if not await _is_agro(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    page = int(call.data.split(":")[2])
    orders = [o async for o in Order.objects.filter(
        agronomist__telegram_id=call.from_user.id,
        status__in=[OrderStatus.APPROVED, OrderStatus.IN_PROGRESS, OrderStatus.PENDING],
    ).order_by('-created_at').aiterator()]

    await bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=orders_list_keyboard(orders, page=page),
    )
    await bot.answer_callback_query(call.id)


# ── Cancel order ──────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("agro:cancel:"))
async def agro_cb_cancel_order(call: types.CallbackQuery):
    if not await _is_agro(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    order_id = int(call.data.split(":")[2])
    await StateManager.set_state(
        call.from_user.id,
        AgronomistStates.ENTER_CANCEL_REASON,
        data={'order_id': order_id},
    )
    await bot.send_message(
        call.message.chat.id,
        f"❌ Buyurtma #{order_id} uchun bekor qilish sababini yozing:",
        reply_markup=cancel_keyboard(),
    )
    await bot.answer_callback_query(call.id)


# ── Complete order — entry point ───────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("agro:complete:"))
async def agro_cb_complete_order(call: types.CallbackQuery):
    if not await _is_agro(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    order_id = int(call.data.split(":")[2])
    try:
        order = await Order.objects.aget(
            pk=order_id, agronomist__telegram_id=call.from_user.id
        )
    except Order.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Buyurtma topilmadi")
        return

    if order.status not in (OrderStatus.APPROVED, OrderStatus.IN_PROGRESS, OrderStatus.PENDING):
        await bot.answer_callback_query(call.id, "⚠️ Bu buyurtma allaqachon yakunlangan yoki bekor qilingan")
        return

    await StateManager.set_state(
        call.from_user.id,
        AgronomistStates.ENTER_TREATMENT_COUNT,
        data={'order_id': order_id},
    )
    await bot.send_message(
        call.message.chat.id,
        f"✅ Buyurtma #{order_id} yakunlash jarayoni boshlandi.\n\n"
        f"🔢 Nechta ishlov berildi? (raqam kiriting):",
        reply_markup=cancel_keyboard(),
    )
    await bot.answer_callback_query(call.id)


# ── Cancel mid-flow ───────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "❌ Bekor qilish")
async def agro_cancel_flow(message: types.Message):
    state = await StateManager.get_state(message.from_user.id)
    if state and state.startswith("agro:"):
        await StateManager.clear(message.from_user.id)
        await bot.send_message(
            message.chat.id,
            "❌ Bekor qilindi.",
            reply_markup=agronomist_main_menu(),
        )


# ── Text input router for completion flow ────────────────────────────────────

@bot.message_handler(func=lambda m: True, content_types=['text'])
async def agro_text_router(message: types.Message):
    if not await _is_agro(message.from_user.id):
        return

    state, data = await StateManager.get_state_and_data(message.from_user.id)
    if not state or not state.startswith("agro:"):
        return

    text = message.text.strip()
    tid = message.from_user.id

    # ── Cancel reason ─────────────────────────────────────────────────────────
    if state == AgronomistStates.ENTER_CANCEL_REASON:
        order_id = data.get('order_id')
        try:
            order = await Order.objects.select_related('client', 'sales_manager').aget(
                pk=order_id, agronomist__telegram_id=tid
            )
        except Order.DoesNotExist:
            await StateManager.clear(tid)
            await bot.send_message(message.chat.id, "❌ Buyurtma topilmadi.", reply_markup=agronomist_main_menu())
            return

        order.status = OrderStatus.CANCELLED
        order.cancel_reason = text
        await order.asave(update_fields=['status', 'cancel_reason', 'updated_at'])
        await StateManager.clear(tid)

        await bot.send_message(
            message.chat.id,
            f"✅ Buyurtma #{order_id} bekor qilindi.",
            reply_markup=agronomist_main_menu(),
        )

        # Notify client
        if order.client:
            await notify_user(
                bot, order.client.telegram_id,
                f"❌ Buyurtma #{order_id} bekor qilindi.\nSabab: {text}"
            )

        # Notify admin & sales manager
        cancel_text = (
            f"❌ <b>Buyurtma #{order_id} bekor qilindi</b>\n"
            f"Agronom: {(await TelegramUser.objects.aget(telegram_id=tid)).full_name}\n"
            f"Sabab: {text}"
        )
        await notify_admins(bot, cancel_text)
        await notify_user(bot, order.sales_manager.telegram_id, cancel_text)

    # ── Treatment count ───────────────────────────────────────────────────────
    elif state == AgronomistStates.ENTER_TREATMENT_COUNT:
        if not text.isdigit() or int(text) < 1:
            await bot.send_message(message.chat.id, "⚠️ Faqat musbat son kiriting:")
            return
        await StateManager.update_data(tid, treatment_count=int(text))
        await StateManager.set_state(tid, AgronomistStates.ENTER_ROOT_TREATMENT)
        await bot.send_message(
            message.chat.id,
            "🌿 Ildizga ishlov berildi?",
            reply_markup=root_treatment_keyboard(),
        )

    # ── Final price ───────────────────────────────────────────────────────────
    elif state == AgronomistStates.ENTER_FINAL_PRICE:
        price_str = text.replace(',', '.').replace(' ', '')
        try:
            price = float(price_str)
            if price < 0:
                raise ValueError
        except ValueError:
            await bot.send_message(message.chat.id, "⚠️ To'g'ri narx kiriting (masalan: 150000):")
            return
        await StateManager.update_data(tid, final_price=price_str)
        await StateManager.set_state(tid, AgronomistStates.SELECT_PAYMENT_TYPE)
        await bot.send_message(
            message.chat.id,
            f"✅ Narx: <b>{price:,.0f} so'm</b>\n\n💳 To'lov turini tanlang:",
            reply_markup=payment_type_keyboard(),
        )

    # ── Re-treatment date ─────────────────────────────────────────────────────
    elif state == AgronomistStates.ENTER_RETREATMENT_DATE:
        try:
            dt = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            await bot.send_message(message.chat.id, "⚠️ Sana formati: KK.OO.YYYY (masalan: 25.04.2024):")
            return
        await StateManager.update_data(tid, re_treatment_date=str(dt))
        await StateManager.set_state(tid, AgronomistStates.UPLOAD_PROOF)
        await bot.send_message(
            message.chat.id,
            f"✅ Qayta ishlov sanasi: <b>{dt}</b>\n\n📸 Ish isbotnomasi uchun foto yoki video yuboring:",
        )


# ── Inline callback handlers for completion flow ──────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("root:"))
async def agro_cb_root_treatment(call: types.CallbackQuery):
    if not await _is_agro(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    state = await StateManager.get_state(call.from_user.id)
    if state != AgronomistStates.ENTER_ROOT_TREATMENT:
        await bot.answer_callback_query(call.id)
        return

    root_applied = call.data.split(":")[1] == "yes"
    await StateManager.update_data(call.from_user.id, root_treatment_applied=root_applied)
    await StateManager.set_state(call.from_user.id, AgronomistStates.ENTER_FINAL_PRICE)

    label = "Ha ✅" if root_applied else "Yo'q ❌"
    await bot.edit_message_text(
        f"✅ Ildiz ishlov: <b>{label}</b>\n\n💰 Kelishilgan yakuniy narxni kiriting (so'mda):",
        call.message.chat.id,
        call.message.message_id,
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("payment:"))
async def agro_cb_payment_type(call: types.CallbackQuery):
    if not await _is_agro(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    state = await StateManager.get_state(call.from_user.id)
    if state != AgronomistStates.SELECT_PAYMENT_TYPE:
        await bot.answer_callback_query(call.id)
        return

    payment_type = call.data.split(":")[1]
    await StateManager.update_data(call.from_user.id, payment_type=payment_type)
    await StateManager.set_state(call.from_user.id, AgronomistStates.SELECT_RETREATMENT)

    payment_labels = {'cash': 'Naqd pul 💵', 'card': 'Karta 💳', 'bank_transfer': "Bank o'tkazmasi 🏦"}
    label = payment_labels.get(payment_type, payment_type)
    await bot.edit_message_text(
        f"✅ To'lov: <b>{label}</b>\n\n🔁 Qayta ishlov kerakmi?",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=retreatment_keyboard(),
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("retreatment:"))
async def agro_cb_retreatment(call: types.CallbackQuery):
    if not await _is_agro(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    state = await StateManager.get_state(call.from_user.id)
    if state != AgronomistStates.SELECT_RETREATMENT:
        await bot.answer_callback_query(call.id)
        return

    needed = call.data.split(":")[1] == "yes"
    await StateManager.update_data(call.from_user.id, re_treatment_needed=needed)

    if needed:
        await StateManager.set_state(call.from_user.id, AgronomistStates.ENTER_RETREATMENT_DATE)
        await bot.edit_message_text(
            "📅 Qayta ishlov sanasini kiriting (KK.OO.YYYY):",
            call.message.chat.id,
            call.message.message_id,
        )
    else:
        await StateManager.set_state(call.from_user.id, AgronomistStates.UPLOAD_PROOF)
        await bot.edit_message_text(
            "📸 Ish isbotnomasi uchun foto yoki video yuboring:",
            call.message.chat.id,
            call.message.message_id,
        )
    await bot.answer_callback_query(call.id)


# ── Photo/Video upload — finalize order ──────────────────────────────────────

@bot.message_handler(func=lambda m: True, content_types=['photo', 'video'])
async def agro_proof_upload(message: types.Message):
    if not await _is_agro(message.from_user.id):
        return

    state, data = await StateManager.get_state_and_data(message.from_user.id)
    if state != AgronomistStates.UPLOAD_PROOF:
        return

    order_id = data.get('order_id')
    if not order_id:
        await bot.send_message(message.chat.id, "❌ Xatolik: buyurtma ID topilmadi.")
        await StateManager.clear(message.from_user.id)
        return

    # Get file_id and type
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
        if data.get('re_treatment_date'):
            re_date = datetime.strptime(data['re_treatment_date'], "%Y-%m-%d").date()

        details = await TreatmentDetails.objects.acreate(
            order=order,
            treatment_count=data['treatment_count'],
            root_treatment_applied=data.get('root_treatment_applied', False),
            final_price=data['final_price'],
            payment_type=data['payment_type'],
            re_treatment_needed=data.get('re_treatment_needed', False),
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

    await StateManager.clear(message.from_user.id)
    await bot.send_message(
        message.chat.id,
        f"✅ <b>Buyurtma #{order_id} yakunlandi!</b>\nMa'lumotlar saqlandi.",
        reply_markup=agronomist_main_menu(),
    )

    # Notify client
    if order.client:
        from bot.keyboards.client_kb import client_service_done_keyboard
        client_text = (
            f"✅ <b>Xizmat bajarildi!</b>\n\n"
            f"Order #{order_id} bo'yicha ishlov yakunlandi.\n"
            f"Iltimos, xizmatni tasdiqlang yoki rad eting:"
        )
        await notify_user(
            bot, order.client.telegram_id, client_text,
            reply_markup=client_service_done_keyboard(order_id)
        )

    # Notify sales manager
    summary = (
        f"✅ <b>Buyurtma #{order_id} yakunlandi</b>\n"
        f"Mijoz: {order.client_name}\n"
        + details.get_summary()
    )
    await notify_user(bot, order.sales_manager.telegram_id, summary)
    await notify_admins(bot, summary)
