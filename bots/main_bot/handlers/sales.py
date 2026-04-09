"""
Sales manager flow:
1. Sales creates order (existing flow)
2. Sales accepts client-created orders (new flow)
"""
import logging
import re
from telebot.states.asyncio.context import StateContext

from bots.main_bot.loader import bot, handler
from bots.main_bot.states import SalesStates
from bots.main_bot.keyboards.sales import (
    sales_main_menu, cancel_keyboard, agronomist_list_keyboard,
    time_slot_keyboard, confirm_order_keyboard,
    client_order_accept_keyboard, assign_agro_keyboard, assign_slot_keyboard,
)
from bots.main_bot.keyboards.admin import approve_order_keyboard
from bots.main_bot.keyboards.agronomist import order_actions_keyboard
from bots.base.sender import Sender
from core.callbacks import (
    agro_select_factory, slot_factory, order_confirm_factory,
    sales_accept_client_order_factory, sales_assign_agro_factory, sales_assign_slot_factory,
)
from core.helpers import notify_user, notify_admins, format_order_card
from core.locks import try_lock, release_lock
from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order, OrderStatus, OrderSource, TimeSlot

logger = logging.getLogger(__name__)
PHONE_RE = re.compile(r'^\+?[0-9]{9,15}$')


# ── /start ────────────────────────────────────────────────────────────────────

@handler(commands=['start'], is_sales=True)
async def sales_start(sender: Sender, state: StateContext):
    await state.delete()
    user = await TelegramUser.objects.aget(telegram_id=sender.user_id)
    await sender.text(
        f"👋 Xush kelibsiz, <b>{user.full_name}</b>!\n\nSotuvchi paneli:",
        markup=sales_main_menu(),
    )


# ── Create order — entry ──────────────────────────────────────────────────────

@handler(text=["📝 Buyurtma yaratish"], is_sales=True)
async def sales_create_order_start(sender: Sender, state: StateContext):
    agronomists = []
    async for agro in TelegramUser.objects.filter(role=UserRole.AGRONOMIST, is_active=True).aiterator():
        agronomists.append(agro)

    if not agronomists:
        await sender.text("⚠️ Hozircha faol agronomlar yo'q.")
        return

    await state.set(SalesStates.SELECT_AGRONOMIST)
    await sender.text(
        "🌱 Agronomni tanlang:",
        markup=agronomist_list_keyboard(agronomists),
    )


# ── Cancel mid-flow ───────────────────────────────────────────────────────────

@handler(text=["❌ Bekor qilish"], is_sales=True, state=[
    SalesStates.SELECT_AGRONOMIST, SalesStates.SELECT_TIME_SLOT,
    SalesStates.ENTER_CLIENT_NAME, SalesStates.ENTER_PHONE1,
    SalesStates.ENTER_PHONE2, SalesStates.ENTER_TREE_COUNT,
    SalesStates.ENTER_PROBLEM, SalesStates.ENTER_ADDRESS,
    SalesStates.CONFIRM_ORDER,
])
async def sales_cancel_flow(sender: Sender, state: StateContext):
    await state.delete()
    await sender.text("❌ Bekor qilindi.", markup=sales_main_menu())


# ── Step 1: Select agronomist ─────────────────────────────────────────────────

@handler(callback=True, config=agro_select_factory.filter(), is_sales=True, state=SalesStates.SELECT_AGRONOMIST)
async def sales_select_agronomist(sender: Sender, state: StateContext):
    cb = agro_select_factory.parse(sender.msg.data)
    agro_id = int(cb['agro_id'])

    try:
        agro = await TelegramUser.objects.aget(pk=agro_id, role=UserRole.AGRONOMIST, is_active=True)
    except TelegramUser.DoesNotExist:
        await sender.answer("❌ Agronom topilmadi", show_alert=True)
        return

    await state.add_data(agronomist_id=agro_id, agronomist_name=agro.full_name)
    await state.set(SalesStates.SELECT_TIME_SLOT)

    # Find today's busy slots for this agronomist
    from django.utils import timezone
    today = timezone.now().date()
    busy = []
    async for o in Order.objects.filter(
        agronomist_id=agro_id,
        status__in=[OrderStatus.PENDING, OrderStatus.APPROVED, OrderStatus.IN_PROGRESS],
    ).aiterator():
        if o.time_slot:
            busy.append(o.time_slot)

    await sender.edit_text(f"✅ Agronom: <b>{agro.full_name}</b>")
    await sender.text("⏰ Vaqt oralig'ini tanlang:", markup=time_slot_keyboard(busy))
    await sender.answer()


# ── Step 2: Select time slot ──────────────────────────────────────────────────

@handler(callback=True, config=slot_factory.filter(), is_sales=True, state=SalesStates.SELECT_TIME_SLOT)
async def sales_select_slot(sender: Sender, state: StateContext):
    cb = slot_factory.parse(sender.msg.data)
    slot_choices = list(TimeSlot.choices)
    try:
        idx = int(cb['slot'])
        slot_value, slot_label = slot_choices[idx]
    except (ValueError, IndexError):
        await sender.answer("❌ Noto'g'ri vaqt", show_alert=True)
        return

    await state.add_data(time_slot=slot_value)
    await state.set(SalesStates.ENTER_CLIENT_NAME)
    await sender.edit_text(f"✅ Vaqt: <b>{slot_label}</b>")
    await sender.text("👤 Mijozning to'liq ismini kiriting:", markup=cancel_keyboard())
    await sender.answer()


# ── Step 3: Client name ───────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_CLIENT_NAME)
async def sales_enter_client_name(sender: Sender, state: StateContext):
    text = sender.msg.text.strip()
    if len(text) < 2:
        await sender.text("⚠️ Ism juda qisqa. Qayta kiriting:")
        return
    await state.add_data(client_name=text)
    await state.set(SalesStates.ENTER_PHONE1)
    await sender.text(f"✅ Ism: <b>{text}</b>\n\n📞 Birinchi telefon raqamini kiriting:")


# ── Step 4: Phone 1 ───────────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_PHONE1)
async def sales_enter_phone1(sender: Sender, state: StateContext):
    text = sender.msg.text.strip()
    if not PHONE_RE.match(text):
        await sender.text("⚠️ Noto'g'ri telefon raqami. Qayta kiriting:")
        return
    await state.add_data(phone1=text)
    await state.set(SalesStates.ENTER_PHONE2)
    await sender.text(f"✅ Tel 1: <b>{text}</b>\n\n📞 Ikkinchi telefon (yoki /skip):")


# ── Step 5: Phone 2 ───────────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_PHONE2)
async def sales_enter_phone2(sender: Sender, state: StateContext):
    text = sender.msg.text.strip()
    phone2 = None
    if text.lower() not in ('/skip', 'skip', '-'):
        if not PHONE_RE.match(text):
            await sender.text("⚠️ Noto'g'ri raqam. /skip yozing o'tkazib yuborish uchun:")
            return
        phone2 = text
    await state.add_data(phone2=phone2)
    await state.set(SalesStates.ENTER_TREE_COUNT)
    await sender.text("🌳 Daraxt sonini kiriting (raqam):")


# ── Step 6: Tree count ────────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_TREE_COUNT, is_digit=True)
async def sales_enter_tree_count(sender: Sender, state: StateContext):
    count = int(sender.msg.text.strip())
    if count < 1:
        await sender.text("⚠️ Faqat musbat son kiriting:")
        return
    await state.add_data(tree_count=count)
    await state.set(SalesStates.ENTER_PROBLEM)
    await sender.text("🔴 Muammo/kasallikni yozing:")


@handler(is_sales=True, state=SalesStates.ENTER_TREE_COUNT, is_digit=False)
async def sales_enter_tree_count_invalid(sender: Sender, state: StateContext):
    await sender.text("⚠️ Faqat raqam kiriting:")


# ── Step 7: Problem ───────────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_PROBLEM)
async def sales_enter_problem(sender: Sender, state: StateContext):
    text = sender.msg.text.strip()
    if len(text) < 5:
        await sender.text("⚠️ Muammoani batafsil yozing (kamida 5 ta harf):")
        return
    await state.add_data(problem=text)
    await state.set(SalesStates.ENTER_ADDRESS)
    await sender.text("📍 Manzilni kiriting:")


# ── Step 8: Address ───────────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_ADDRESS)
async def sales_enter_address(sender: Sender, state: StateContext):
    text = sender.msg.text.strip()
    if len(text) < 5:
        await sender.text("⚠️ Manzilni to'liqroq yozing:")
        return

    await state.add_data(address=text)
    await state.set(SalesStates.CONFIRM_ORDER)

    async with state.data() as data:
        slot_label = dict(TimeSlot.choices).get(data.get('time_slot', ''), '—')
        summary = (
            f"📋 <b>Buyurtma ma'lumotlari:</b>\n\n"
            f"🌱 Agronom: {data.get('agronomist_name')}\n"
            f"⏰ Vaqt: {slot_label}\n"
            f"👤 Mijoz: {data.get('client_name')}\n"
            f"📞 Tel 1: {data.get('phone1')}\n"
            f"📞 Tel 2: {data.get('phone2') or '—'}\n"
            f"🌳 Daraxt: {data.get('tree_count')}\n"
            f"🔴 Muammo: {data.get('problem')}\n"
            f"📍 Manzil: {text}"
        )

    await sender.text(summary, markup=confirm_order_keyboard())


# ── Step 9: Confirm ───────────────────────────────────────────────────────────

@handler(callback=True, config=order_confirm_factory.filter(), is_sales=True, state=SalesStates.CONFIRM_ORDER)
async def sales_confirm_order(sender: Sender, state: StateContext):
    cb = order_confirm_factory.parse(sender.msg.data)
    if cb['answer'] == 'no':
        await state.delete()
        await sender.edit_markup()
        await sender.text("❌ Bekor qilindi.", markup=sales_main_menu())
        await sender.answer()
        return

    async with state.data() as data:
        agro_id = data['agronomist_id']
        client_name = data['client_name']
        phone1 = data['phone1']
        phone2 = data.get('phone2') or ''
        tree_count = data['tree_count']
        problem = data['problem']
        address = data['address']
        time_slot = data['time_slot']

    try:
        sales_user = await TelegramUser.objects.aget(telegram_id=sender.user_id)
        agro = await TelegramUser.objects.aget(pk=agro_id)

        # Try to find client by phone for notification
        client = None
        try:
            client = await TelegramUser.objects.aget(phone=phone1, role=UserRole.CLIENT)
        except TelegramUser.DoesNotExist:
            pass

        # Status depends on whether client has bot account
        initial_status = OrderStatus.AWAITING_CLIENT if client else OrderStatus.PENDING

        order = await Order.objects.acreate(
            sales_manager=sales_user,
            agronomist=agro,
            client=client,
            client_name=client_name,
            phone1=phone1,
            phone2=phone2,
            tree_count=tree_count,
            problem=problem,
            address=address,
            time_slot=time_slot,
            source=OrderSource.SALES_CREATED,
            status=initial_status,
        )
    except Exception as exc:
        logger.error("Order creation failed: %s", exc)
        await sender.text("❌ Xatolik yuz berdi. Qayta urinib ko'ring.", markup=sales_main_menu())
        await sender.answer()
        return

    await state.delete()
    await sender.edit_markup()
    await sender.text(f"✅ Buyurtma #{order.pk} yaratildi!", markup=sales_main_menu())
    await sender.answer(f"✅ Buyurtma #{order.pk} yaratildi!")

    # Notify client for confirmation (if found in client bot)
    if client and initial_status == OrderStatus.AWAITING_CLIENT:
        await _notify_client_for_confirmation(order, client)
    else:
        # Directly notify agronomist and admins
        await _notify_order_created(order, agro)


async def _notify_client_for_confirmation(order: Order, client: TelegramUser):
    """Notify client via client bot to confirm the order."""
    try:
        from bots.client_bot.loader import bot as client_bot
        from bots.client_bot.keyboards.client import order_notification_keyboard
        from core.helpers import format_order_card
        from core.i18n import t

        lang = client.language or 'uz'
        text = t('order_notification', lang,
                 order_id=order.pk,
                 order_card=format_order_card(order))
        await notify_user(client_bot, client.telegram_id, text,
                          reply_markup=order_notification_keyboard(order.pk, lang))
    except Exception as exc:
        logger.error("Failed to notify client %s: %s", client.telegram_id, exc)
        # Fallback: set status to pending and notify agronomist
        await Order.objects.filter(pk=order.pk).aupdate(status=OrderStatus.PENDING)
        agro = order.agronomist
        await _notify_order_created(order, agro)


async def _notify_order_created(order: Order, agro: TelegramUser):
    """Notify agronomist and admins about new order (after all confirmations)."""
    await notify_user(
        bot, agro.telegram_id,
        f"🆕 <b>Yangi buyurtma #{order.pk}</b>\n\n" + format_order_card(order),
        reply_markup=order_actions_keyboard(order.pk),
    )
    await notify_admins(
        bot,
        f"🆕 Yangi buyurtma #{order.pk} yaratildi.\n\n" + format_order_card(order),
        reply_markup=approve_order_keyboard(order.pk),
    )


# ── View client orders (AWAITING_SALES) ──────────────────────────────────────

@handler(text=["📋 Client so'rovlari"], is_sales=True)
async def sales_view_client_orders(sender: Sender, state: StateContext):
    orders = []
    async for o in Order.objects.filter(
        status=OrderStatus.AWAITING_SALES
    ).select_related('client').aiterator():
        orders.append(o)

    if not orders:
        await sender.text("📭 Hozircha client so'rovlari yo'q.")
        return

    for order in orders:
        card = (
            f"📋 <b>Buyurtma #{order.pk}</b> — Client so'rovi\n\n"
            f"👤 {order.client_name}\n"
            f"📞 {order.phone1}\n"
            f"🔴 {order.problem}\n"
            f"📍 {order.address}\n"
            f"🌳 {order.tree_count} daraxt"
        )
        await bot.send_message(
            sender.chat_id, card,
            reply_markup=client_order_accept_keyboard(order.pk),
        )


# ── Accept client order ───────────────────────────────────────────────────────

@handler(callback=True, config=sales_accept_client_order_factory.filter(), is_sales=True)
async def sales_accept_client_order(sender: Sender, state: StateContext):
    cb = sales_accept_client_order_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])

    lock_key = f"accept_order:{order_id}"
    if not await try_lock(lock_key, ttl=10):
        await sender.answer("⏳ Allaqachon qayta ishlanmoqda...", show_alert=True)
        return

    try:
        order = await Order.objects.aget(pk=order_id, status=OrderStatus.AWAITING_SALES)
    except Order.DoesNotExist:
        await sender.answer("⚠️ Bu buyurtma allaqachon qabul qilingan.", show_alert=True)
        await release_lock(lock_key)
        return

    # Get agronomists for assignment
    agronomists = []
    async for agro in TelegramUser.objects.filter(role=UserRole.AGRONOMIST, is_active=True).aiterator():
        agronomists.append(agro)

    if not agronomists:
        await sender.answer("⚠️ Faol agronomlar yo'q!", show_alert=True)
        await release_lock(lock_key)
        return

    await state.set(SalesStates.ACCEPT_CLIENT_ORDER_SELECT_AGRO)
    await state.add_data(accepting_order_id=order_id)
    await release_lock(lock_key)

    await sender.edit_text(
        f"✅ Buyurtma #{order_id} uchun agronomni tanlang:",
        markup=assign_agro_keyboard(order_id, agronomists),
    )
    await sender.answer()


@handler(callback=True, config=sales_assign_agro_factory.filter(), is_sales=True,
         state=SalesStates.ACCEPT_CLIENT_ORDER_SELECT_AGRO)
async def sales_assign_agro_to_client_order(sender: Sender, state: StateContext):
    cb = sales_assign_agro_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])
    agro_id = int(cb['agro_id'])

    await state.add_data(assigning_agro_id=agro_id)
    await state.set(SalesStates.ACCEPT_CLIENT_ORDER_SELECT_SLOT)

    # Find busy slots for this agronomist
    busy = []
    async for o in Order.objects.filter(
        agronomist_id=agro_id,
        status__in=[OrderStatus.PENDING, OrderStatus.APPROVED, OrderStatus.IN_PROGRESS],
    ).aiterator():
        if o.time_slot:
            busy.append(o.time_slot)

    await sender.edit_text(
        f"⏰ Buyurtma #{order_id} uchun vaqt tanlang:",
        markup=assign_slot_keyboard(order_id, busy),
    )
    await sender.answer()


@handler(callback=True, config=sales_assign_slot_factory.filter(), is_sales=True,
         state=SalesStates.ACCEPT_CLIENT_ORDER_SELECT_SLOT)
async def sales_assign_slot_to_client_order(sender: Sender, state: StateContext):
    cb = sales_assign_slot_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])
    slot_choices = list(TimeSlot.choices)
    try:
        idx = int(cb['slot'])
        slot_value, slot_label = slot_choices[idx]
    except (ValueError, IndexError):
        await sender.answer("❌ Noto'g'ri vaqt", show_alert=True)
        return

    async with state.data() as data:
        agro_id = data.get('assigning_agro_id')

    try:
        order = await Order.objects.select_related('client').aget(pk=order_id)
        agro = await TelegramUser.objects.aget(pk=agro_id)
        sales_user = await TelegramUser.objects.aget(telegram_id=sender.user_id)
    except Exception as exc:
        logger.error("sales_assign_slot: %s", exc)
        await sender.answer("❌ Xatolik", show_alert=True)
        return

    await Order.objects.filter(pk=order_id).aupdate(
        sales_manager=sales_user,
        agronomist=agro,
        time_slot=slot_value,
        status=OrderStatus.PENDING,
    )
    await state.delete()

    await sender.edit_text(
        f"✅ Buyurtma #{order_id} qabul qilindi!\n"
        f"🌱 Agronom: {agro.full_name}\n"
        f"⏰ Vaqt: {slot_label}",
    )
    await sender.answer("✅ Muvaffaqiyatli!")

    # Refresh order for notifications
    order = await Order.objects.select_related('client', 'agronomist', 'sales_manager').aget(pk=order_id)

    await notify_admins(
        bot,
        f"🆕 Yangi buyurtma #{order.pk} (client tomonidan).\n\n" + format_order_card(order),
        reply_markup=approve_order_keyboard(order.pk),
    )

    # Notify client that order was accepted
    if order.client_id:
        try:
            from bots.client_bot.loader import bot as client_bot
            from core.i18n import t
            lang = order.client.language or 'uz'
            await notify_user(
                client_bot, order.client.telegram_id,
                t('order_accepted_msg', lang) + f"\n\nBuyurtma #{order.pk}",
            )
        except Exception as exc:
            logger.error("Client notify failed: %s", exc)


# ── View all orders ───────────────────────────────────────────────────────────

@handler(text=["📦 Barcha buyurtmalar"], is_sales=True)
async def sales_all_orders(sender: Sender, state: StateContext):
    user = await TelegramUser.objects.aget(telegram_id=sender.user_id)
    orders = []
    async for o in Order.objects.filter(
        sales_manager=user,
        status__in=[OrderStatus.AWAITING_CLIENT, OrderStatus.PENDING,
                    OrderStatus.APPROVED, OrderStatus.IN_PROGRESS],
    ).select_related('agronomist').aiterator():
        orders.append(o)

    if not orders:
        await sender.text("📭 Faol buyurtmalar yo'q.")
        return

    lines = []
    for o in orders:
        lines.append(f"• #{o.pk} — {o.client_name} | {o.status}")
    await sender.text("📦 <b>Sizning buyurtmalaringiz:</b>\n\n" + "\n".join(lines))
