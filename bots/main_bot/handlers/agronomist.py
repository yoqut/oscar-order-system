"""
Agronomist flow — view assigned orders, cancel, complete with treatment details.
All navigation via inline callbacks; text input only for actual data entry.
"""
import logging
from datetime import datetime
from telebot.states.asyncio.context import StateContext

from bots.main_bot.loader import bot, handler
from bots.main_bot.states import AgronomistStates
from bots.main_bot.keyboards.agronomist import (
    agronomist_main_menu, cancel_keyboard, orders_list_keyboard,
    order_actions_keyboard, root_treatment_keyboard, payment_type_keyboard,
    retreatment_keyboard,
)
from bots.base.sender import Sender
from core.callbacks import (
    agro_view_factory, agro_cancel_factory, agro_complete_factory,
    agro_page_factory, root_factory, payment_factory, retreatment_factory,
)
from core.helpers import notify_user, notify_admins, format_order_card
from core.locks import try_lock, release_lock
from apps.accounts.models import TelegramUser
from apps.orders.models import Order, OrderStatus, TreatmentDetails

logger = logging.getLogger(__name__)


# ── /start ────────────────────────────────────────────────────────────────────

@handler(commands=['start'], is_agronomist=True)
async def agro_start(sender: Sender, state: StateContext):
    await state.delete()
    user = await TelegramUser.objects.aget(telegram_id=sender.user_id)
    await sender.text(
        f"🌱 Xush kelibsiz, <b>{user.full_name}</b>!\n\nAgronom paneli:",
        markup=agronomist_main_menu(),
    )


# ── View my orders ────────────────────────────────────────────────────────────

@handler(callback=True, call='agro:my_orders', is_agronomist=True)
async def agro_my_orders(sender: Sender, state: StateContext):
    await state.delete()
    user = await TelegramUser.objects.aget(telegram_id=sender.user_id)
    orders = []
    async for o in Order.objects.filter(
        agronomist=user,
        status__in=[OrderStatus.APPROVED, OrderStatus.IN_PROGRESS, OrderStatus.PENDING],
    ).select_related('client').aiterator():
        orders.append(o)

    if not orders:
        await sender.edit_text("📭 Hozircha buyurtmalar yo'q.", markup=agronomist_main_menu())
        await sender.answer()
        return

    await sender.edit_text(
        f"📋 <b>Sizning buyurtmalaringiz ({len(orders)} ta):</b>",
        markup=orders_list_keyboard(orders, page=0),
    )
    await sender.answer()


@handler(callback=True, config=agro_page_factory.filter(), is_agronomist=True)
async def agro_paginate(sender: Sender, state: StateContext):
    cb = agro_page_factory.parse(sender.msg.data)
    page = int(cb['page'])
    user = await TelegramUser.objects.aget(telegram_id=sender.user_id)
    orders = []
    async for o in Order.objects.filter(
        agronomist=user,
        status__in=[OrderStatus.APPROVED, OrderStatus.IN_PROGRESS, OrderStatus.PENDING],
    ).aiterator():
        orders.append(o)

    await sender.edit_markup(markup=orders_list_keyboard(orders, page=page))
    await sender.answer()


# ── View single order ─────────────────────────────────────────────────────────

@handler(callback=True, config=agro_view_factory.filter(), is_agronomist=True)
async def agro_view_order(sender: Sender, state: StateContext):
    cb = agro_view_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])
    try:
        order = await Order.objects.select_related('client', 'sales_manager').aget(pk=order_id)
    except Order.DoesNotExist:
        await sender.answer("❌ Buyurtma topilmadi", show_alert=True)
        return

    await sender.edit_text(format_order_card(order), markup=order_actions_keyboard(order_id))
    await sender.answer()


# ── Cancel order ──────────────────────────────────────────────────────────────

@handler(callback=True, config=agro_cancel_factory.filter(), is_agronomist=True)
async def agro_cancel_start(sender: Sender, state: StateContext):
    cb = agro_cancel_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])
    await state.set(AgronomistStates.ENTER_CANCEL_REASON)
    await state.add_data(order_id=order_id)
    await sender.edit_text(
        "❌ Bekor qilish sababini yozing:",
        markup=cancel_keyboard(),
    )
    await sender.answer()


@handler(callback=True, call='agro:cancel', is_agronomist=True, state=[
    AgronomistStates.ENTER_CANCEL_REASON,
    AgronomistStates.ENTER_TREATMENT_COUNT,
    AgronomistStates.ENTER_FINAL_PRICE,
    AgronomistStates.ENTER_RETREATMENT_DATE,
    AgronomistStates.UPLOAD_PROOF,
])
async def agro_cancel_abort(sender: Sender, state: StateContext):
    await state.delete()
    await sender.edit_text("↩️ Bekor qilindi.")
    await sender.text("Agronom paneli:", markup=agronomist_main_menu())
    await sender.answer()


# ── Complete order — step 1: treatment count ──────────────────────────────────

@handler(callback=True, config=agro_complete_factory.filter(), is_agronomist=True)
async def agro_complete_start(sender: Sender, state: StateContext):
    cb = agro_complete_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])

    lock_key = f"complete_order:{order_id}"
    if not await try_lock(lock_key, ttl=30):
        await sender.answer("⏳ Allaqachon qayta ishlanmoqda...", show_alert=True)
        return

    try:
        order = await Order.objects.aget(pk=order_id)
    except Order.DoesNotExist:
        await sender.answer("❌ Topilmadi", show_alert=True)
        await release_lock(lock_key)
        return

    if order.status not in (OrderStatus.APPROVED, OrderStatus.IN_PROGRESS):
        await sender.answer("⚠️ Bu buyurtma bajarilmaydi.", show_alert=True)
        await release_lock(lock_key)
        return

    await Order.objects.filter(pk=order_id).aupdate(status=OrderStatus.IN_PROGRESS)
    await state.set(AgronomistStates.ENTER_TREATMENT_COUNT)
    await state.add_data(order_id=order_id)
    await release_lock(lock_key)

    await sender.edit_text("🔢 Ishlov sonini kiriting (raqam):", markup=cancel_keyboard())
    await sender.answer()


@handler(is_agronomist=True, state=AgronomistStates.ENTER_TREATMENT_COUNT, is_digit=True)
async def agro_enter_treatment_count(sender: Sender, state: StateContext):
    count = int(sender.msg.text.strip())
    if count < 1:
        await sender.text("⚠️ Musbat son kiriting:", markup=cancel_keyboard())
        return
    await state.add_data(treatment_count=count)
    await state.set(AgronomistStates.ENTER_ROOT_TREATMENT)
    await sender.text("🌱 Ildiz ishlov berildi?", markup=root_treatment_keyboard())


@handler(is_agronomist=True, state=AgronomistStates.ENTER_TREATMENT_COUNT, is_digit=False)
async def agro_treatment_count_invalid(sender: Sender, state: StateContext):
    await sender.text("⚠️ Faqat raqam kiriting:", markup=cancel_keyboard())


# ── Step 2: Root treatment ────────────────────────────────────────────────────

@handler(callback=True, config=root_factory.filter(), is_agronomist=True,
         state=AgronomistStates.ENTER_ROOT_TREATMENT)
async def agro_root_treatment(sender: Sender, state: StateContext):
    cb = root_factory.parse(sender.msg.data)
    applied = cb['value'] == 'true'
    await state.add_data(root_treatment_applied=applied)
    await state.set(AgronomistStates.ENTER_FINAL_PRICE)
    icon = "✅ Ha" if applied else "❌ Yo'q"
    await sender.edit_text(f"Ildiz ishlov: {icon}")
    await sender.text("💰 Yakuniy narxni kiriting (so'mda):", markup=cancel_keyboard())
    await sender.answer()


# ── Step 3: Final price ───────────────────────────────────────────────────────

@handler(is_agronomist=True, state=AgronomistStates.ENTER_FINAL_PRICE)
async def agro_enter_price(sender: Sender, state: StateContext):
    text = sender.msg.text.strip().replace(',', '.').replace(' ', '').replace("'", '')
    try:
        price = float(text)
        if price < 0:
            raise ValueError
    except ValueError:
        await sender.text("⚠️ To'g'ri narx kiriting (masalan: 150000):", markup=cancel_keyboard())
        return
    await state.add_data(final_price=str(price))
    await state.set(AgronomistStates.SELECT_PAYMENT_TYPE)
    await sender.text("💳 To'lov turini tanlang:", markup=payment_type_keyboard())


# ── Step 4: Payment type ──────────────────────────────────────────────────────

@handler(callback=True, config=payment_factory.filter(), is_agronomist=True,
         state=AgronomistStates.SELECT_PAYMENT_TYPE)
async def agro_select_payment(sender: Sender, state: StateContext):
    cb = payment_factory.parse(sender.msg.data)
    await state.add_data(payment_type=cb['ptype'])
    await state.set(AgronomistStates.SELECT_RETREATMENT)
    await sender.edit_text("🔁 Qayta ishlov kerakmi?", markup=retreatment_keyboard())
    await sender.answer()


# ── Step 5: Re-treatment ──────────────────────────────────────────────────────

@handler(callback=True, config=retreatment_factory.filter(), is_agronomist=True,
         state=AgronomistStates.SELECT_RETREATMENT)
async def agro_select_retreatment(sender: Sender, state: StateContext):
    cb = retreatment_factory.parse(sender.msg.data)
    needed = cb['value'] == 'true'
    await state.add_data(re_treatment_needed=needed)

    if needed:
        await state.set(AgronomistStates.ENTER_RETREATMENT_DATE)
        await sender.edit_text(
            "📅 Qayta ishlov sanasini kiriting (KK.OO.YYYY):",
            markup=cancel_keyboard(),
        )
    else:
        await state.add_data(re_treatment_date=None)
        await state.set(AgronomistStates.UPLOAD_PROOF)
        await sender.edit_text("📸 Ish bajarilganini tasdiqlovchi foto yoki video yuboring:")
    await sender.answer()


@handler(is_agronomist=True, state=AgronomistStates.ENTER_RETREATMENT_DATE)
async def agro_enter_retreatment_date(sender: Sender, state: StateContext):
    text = sender.msg.text.strip() if sender.msg.text else ''
    try:
        d = datetime.strptime(text, '%d.%m.%Y').date()
    except ValueError:
        await sender.text("⚠️ Format: KK.OO.YYYY (masalan: 25.01.2025)", markup=cancel_keyboard())
        return
    await state.add_data(re_treatment_date=str(d))
    await state.set(AgronomistStates.UPLOAD_PROOF)
    await sender.text("📸 Ish bajarilganini tasdiqlovchi foto yoki video yuboring:")


# ── Step 6: Upload proof ──────────────────────────────────────────────────────

@handler(is_agronomist=True, state=AgronomistStates.UPLOAD_PROOF,
         content_types=['photo', 'video'])
async def agro_upload_proof(sender: Sender, state: StateContext):
    msg = sender.msg
    if msg.photo:
        file_id = msg.photo[-1].file_id
        file_type = 'photo'
    elif msg.video:
        file_id = msg.video.file_id
        file_type = 'video'
    else:
        await sender.text("⚠️ Faqat foto yoki video yuboring.")
        return

    async with state.data() as data:
        order_id = data['order_id']
        treatment_count = data['treatment_count']
        root_treatment_applied = data.get('root_treatment_applied', False)
        final_price = float(data['final_price'])
        payment_type = data['payment_type']
        re_treatment_needed = data.get('re_treatment_needed', False)
        re_treatment_date_str = data.get('re_treatment_date')

    re_treatment_date = None
    if re_treatment_date_str:
        from datetime import date
        re_treatment_date = date.fromisoformat(re_treatment_date_str)

    try:
        await TreatmentDetails.objects.acreate(
            order_id=order_id,
            treatment_count=treatment_count,
            root_treatment_applied=root_treatment_applied,
            final_price=final_price,
            payment_type=payment_type,
            re_treatment_needed=re_treatment_needed,
            re_treatment_date=re_treatment_date,
            proof_file_id=file_id,
            proof_file_type=file_type,
        )
        await Order.objects.filter(pk=order_id).aupdate(status=OrderStatus.COMPLETED)
    except Exception as exc:
        logger.error("TreatmentDetails creation failed: %s", exc)
        await sender.text("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
        return

    await state.delete()
    await sender.text("✅ Xizmat bajarildi deb belgilandi!", markup=agronomist_main_menu())

    order = await Order.objects.select_related('client', 'sales_manager', 'agronomist').aget(pk=order_id)
    td = await TreatmentDetails.objects.aget(order_id=order_id)

    if order.client_id:
        await _notify_client_service_completed(order, td)

    if order.sales_manager_id:
        await notify_user(
            bot, order.sales_manager.telegram_id,
            f"✅ Buyurtma #{order_id} bajarildi!\n\n{td.get_summary()}",
        )

    await notify_admins(
        bot,
        f"✅ Buyurtma #{order_id} bajarildi.\n\nAgronom: {order.agronomist.full_name}\n\n{td.get_summary()}",
    )


async def _notify_client_service_completed(order: Order, td: TreatmentDetails):
    try:
        from bots.client_bot.loader import bot as client_bot
        from bots.client_bot.keyboards.client import service_done_keyboard
        from core.i18n import t
        lang = order.client.language or 'uz'
        text = t('service_completed_msg', lang,
                 order_id=order.pk,
                 treatment_summary=td.get_summary())
        await notify_user(
            client_bot, order.client.telegram_id,
            text,
            reply_markup=service_done_keyboard(order.pk, lang),
        )
    except Exception as exc:
        logger.error("Failed to notify client about completion: %s", exc)


# ── Cancel reason text entry ───────────────────────────────────────────────────

@handler(is_agronomist=True, state=AgronomistStates.ENTER_CANCEL_REASON)
async def agro_enter_cancel_reason(sender: Sender, state: StateContext):
    reason = sender.msg.text.strip() if sender.msg.text else ''
    if len(reason) < 3:
        await sender.text("⚠️ Sababni to'liqroq yozing:", markup=cancel_keyboard())
        return

    async with state.data() as data:
        order_id = data.get('order_id')

    if not order_id:
        await state.delete()
        await sender.text("❌ Xatolik.", markup=agronomist_main_menu())
        return

    try:
        order = await Order.objects.select_related('client', 'sales_manager').aget(pk=order_id)
    except Order.DoesNotExist:
        await state.delete()
        await sender.text("❌ Buyurtma topilmadi.", markup=agronomist_main_menu())
        return

    await Order.objects.filter(pk=order_id).aupdate(
        status=OrderStatus.CANCELLED,
        cancel_reason=reason,
    )
    await state.delete()
    await sender.text("✅ Buyurtma bekor qilindi.", markup=agronomist_main_menu())

    if order.client_id:
        try:
            from bots.client_bot.loader import bot as client_bot
            from core.i18n import t
            lang = order.client.language or 'uz'
            await notify_user(
                client_bot, order.client.telegram_id,
                f"{t('order_cancelled_msg', lang)}\n\nBuyurtma #{order_id}\n\nSabab: {reason}",
            )
        except Exception as exc:
            logger.error("Client cancel notify failed: %s", exc)

    if order.sales_manager_id:
        await notify_user(
            bot, order.sales_manager.telegram_id,
            f"❌ Buyurtma #{order_id} agronom tomonidan bekor qilindi.\nSabab: {reason}",
        )
    await notify_admins(
        bot,
        f"❌ Buyurtma #{order_id} bekor qilindi.\nAgronom: {order.agronomist_id}\nSabab: {reason}",
    )
