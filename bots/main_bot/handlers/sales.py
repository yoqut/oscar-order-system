"""
Sales manager flow.

Order creation sequence (sales-initiated):
  name → phone1 → phone2 → tree_count → problem → address
  → date picker (availability) → slot picker (availability)
  → agronomist picker (free only) → confirm → create

Accepting client-created orders:
  accept → assign agronomist → assign slot → notify admins
"""
import logging
import re
from datetime import date, timedelta
from telebot.states.asyncio.context import StateContext

from bots.main_bot.loader import bot, handler
from bots.main_bot.states import SalesStates
from bots.main_bot.keyboards.sales import (
    sales_main_menu, cancel_keyboard, skip_phone2_keyboard,
    date_picker_keyboard, time_slot_keyboard_avail, agronomist_list_keyboard,
    confirm_order_keyboard, client_order_accept_keyboard,
    assign_agro_keyboard, assign_slot_keyboard,
)
from bots.main_bot.keyboards.admin import approve_order_keyboard
from bots.main_bot.keyboards.agronomist import order_actions_keyboard
from bots.base.sender import Sender
from core.callbacks import (
    agro_select_factory, slot_factory, order_confirm_factory,
    sales_accept_client_order_factory, sales_assign_agro_factory,
    sales_assign_slot_factory, sales_date_factory,
)
from core.helpers import notify_user, notify_admins, format_order_card
from core.locks import try_lock, release_lock
from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order, OrderStatus, OrderSource, TimeSlot

logger = logging.getLogger(__name__)
PHONE_RE = re.compile(r'^\+?[0-9]{9,15}$')


# ── /start ─────────────────────────────────────────────────────────────────────

@handler(commands=['start'], is_sales=True)
async def sales_start(sender: Sender, state: StateContext):
    await state.delete()
    user = await TelegramUser.objects.aget(telegram_id=sender.user_id)
    await sender.text(
        f"👋 Xush kelibsiz, <b>{user.full_name}</b>!\n\nSotuvchi paneli:",
        markup=sales_main_menu(),
    )


# ── Main menu callbacks ────────────────────────────────────────────────────────

@handler(callback=True, call='sales:cancel', is_sales=True)
async def sales_cancel_flow(sender: Sender, state: StateContext):
    await state.delete()
    await sender.edit_text("❌ Bekor qilindi.")
    await sender.text("Sotuvchi paneli:", markup=sales_main_menu())
    await sender.answer()


@handler(callback=True, call='sales:create_order', is_sales=True)
async def sales_create_order_start(sender: Sender, state: StateContext):
    await state.set(SalesStates.ENTER_CLIENT_NAME)
    await sender.edit_text(
        "👤 Mijozning to'liq ismini kiriting:",
        markup=cancel_keyboard(),
    )
    await sender.answer()


@handler(callback=True, call='sales:client_requests', is_sales=True)
async def sales_view_client_orders(sender: Sender, state: StateContext):
    orders = []
    async for o in Order.objects.filter(
        status=OrderStatus.AWAITING_SALES
    ).select_related('client').aiterator():
        orders.append(o)

    await sender.answer()
    if not orders:
        await sender.edit_text("📭 Hozircha client so'rovlari yo'q.", markup=sales_main_menu())
        return

    await sender.edit_text(f"📋 {len(orders)} ta client so'rovi:")
    for order in orders:
        card = (
            f"📋 <b>Buyurtma #{order.pk}</b>\n\n"
            f"👤 {order.client_name}\n"
            f"📞 {order.phone1}\n"
            f"🌳 {order.tree_count} daraxt\n"
            f"🔴 {order.problem}\n"
            f"📍 {order.address}"
        )
        await bot.send_message(
            sender.chat_id, card,
            reply_markup=client_order_accept_keyboard(order.pk),
            parse_mode='HTML',
        )


@handler(callback=True, call='sales:my_orders', is_sales=True)
async def sales_all_orders(sender: Sender, state: StateContext):
    user = await TelegramUser.objects.aget(telegram_id=sender.user_id)
    orders = []
    async for o in Order.objects.filter(
        sales_manager=user,
        status__in=[
            OrderStatus.AWAITING_CLIENT, OrderStatus.PENDING,
            OrderStatus.APPROVED, OrderStatus.IN_PROGRESS,
        ],
    ).select_related('agronomist').aiterator():
        orders.append(o)

    await sender.answer()
    if not orders:
        await sender.edit_text("📭 Faol buyurtmalar yo'q.", markup=sales_main_menu())
        return

    lines = []
    for o in orders:
        slot_label = dict(TimeSlot.choices).get(o.time_slot, '—')
        date_str = o.visit_date.strftime('%d.%m.%Y') if o.visit_date else '—'
        lines.append(f"• #{o.pk} — {o.client_name} | {date_str} {slot_label} | {o.get_status_display()}")
    await sender.edit_text(
        "📦 <b>Sizning buyurtmalaringiz:</b>\n\n" + "\n".join(lines),
        markup=sales_main_menu(),
    )


# ── Step 1: Client name ────────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_CLIENT_NAME)
async def sales_enter_client_name(sender: Sender, state: StateContext):
    text = sender.msg.text.strip() if sender.msg.text else ''
    if len(text) < 2:
        await sender.text("⚠️ Ism juda qisqa. Qayta kiriting:", markup=cancel_keyboard())
        return
    await state.add_data(client_name=text)
    await state.set(SalesStates.ENTER_PHONE1)
    await sender.text(
        f"✅ Ism: <b>{text}</b>\n\n📞 Birinchi telefon raqamini kiriting:",
        markup=cancel_keyboard(),
    )


# ── Step 2: Phone 1 ────────────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_PHONE1)
async def sales_enter_phone1(sender: Sender, state: StateContext):
    text = sender.msg.text.strip() if sender.msg.text else ''
    if not PHONE_RE.match(text):
        await sender.text("⚠️ Noto'g'ri telefon raqami. Masalan: +998901234567", markup=cancel_keyboard())
        return
    await state.add_data(phone1=text)
    await state.set(SalesStates.ENTER_PHONE2)
    await sender.text(
        f"✅ Tel 1: <b>{text}</b>\n\n📞 Ikkinchi telefon raqami (yoki o'tkazib yuborish):",
        markup=skip_phone2_keyboard(),
    )


# ── Step 3: Phone 2 ────────────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_PHONE2)
async def sales_enter_phone2_text(sender: Sender, state: StateContext):
    text = sender.msg.text.strip() if sender.msg.text else ''
    if not PHONE_RE.match(text):
        await sender.text("⚠️ Noto'g'ri raqam. Pastdagi tugmani bosib o'tkazing:", markup=skip_phone2_keyboard())
        return
    await state.add_data(phone2=text)
    await state.set(SalesStates.ENTER_TREE_COUNT)
    await sender.text("✅ Tel 2 saqlandi.\n\n🌳 Daraxt sonini kiriting (faqat raqam):", markup=cancel_keyboard())


@handler(callback=True, call='sales:skip_phone2', is_sales=True, state=SalesStates.ENTER_PHONE2)
async def sales_skip_phone2(sender: Sender, state: StateContext):
    await state.add_data(phone2=None)
    await state.set(SalesStates.ENTER_TREE_COUNT)
    await sender.edit_text("⏭ Tel 2 o'tkazildi.\n\n🌳 Daraxt sonini kiriting (faqat raqam):")
    await sender.answer()


# ── Step 4: Tree count ─────────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_TREE_COUNT, is_digit=True)
async def sales_enter_tree_count(sender: Sender, state: StateContext):
    count = int(sender.msg.text.strip())
    if count < 1:
        await sender.text("⚠️ Faqat musbat son kiriting:", markup=cancel_keyboard())
        return
    await state.add_data(tree_count=count)
    await state.set(SalesStates.ENTER_PROBLEM)
    await sender.text(
        f"✅ Daraxt soni: <b>{count}</b>\n\n🔴 Muammo yoki kasallikni yozing:",
        markup=cancel_keyboard(),
    )


@handler(is_sales=True, state=SalesStates.ENTER_TREE_COUNT, is_digit=False)
async def sales_enter_tree_count_invalid(sender: Sender, state: StateContext):
    await sender.text("⚠️ Faqat raqam kiriting:", markup=cancel_keyboard())


# ── Step 5: Problem ────────────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_PROBLEM)
async def sales_enter_problem(sender: Sender, state: StateContext):
    text = sender.msg.text.strip() if sender.msg.text else ''
    if len(text) < 5:
        await sender.text("⚠️ Muammoani batafsil yozing (kamida 5 ta belgi):", markup=cancel_keyboard())
        return
    await state.add_data(problem=text)
    await state.set(SalesStates.ENTER_ADDRESS)
    await sender.text(
        f"✅ Muammo saqlandi.\n\n📍 Aniq manzilni kiriting (ko'cha, uy, orientir):",
        markup=cancel_keyboard(),
    )


# ── Step 6: Address ────────────────────────────────────────────────────────────

@handler(is_sales=True, state=SalesStates.ENTER_ADDRESS)
async def sales_enter_address(sender: Sender, state: StateContext):
    text = sender.msg.text.strip() if sender.msg.text else ''
    if len(text) < 5:
        await sender.text("⚠️ Manzilni to'liqroq yozing:", markup=cancel_keyboard())
        return
    await state.add_data(address=text)
    await state.set(SalesStates.SELECT_DATE)

    date_avail = await _build_date_availability()
    await sender.text("📅 Borish sanasini tanlang:", markup=date_picker_keyboard(date_avail))


# ── Step 7: Date selection ─────────────────────────────────────────────────────

@handler(callback=True, call='date:busy', is_sales=True)
async def sales_date_busy(sender: Sender, state: StateContext):
    await sender.answer("❌ Bu sana barcha agronomlar band!", show_alert=True)


@handler(callback=True, call='slot:busy', is_sales=True)
async def sales_slot_busy(sender: Sender, state: StateContext):
    await sender.answer("❌ Bu vaqtda barcha agronomlar band!", show_alert=True)


@handler(callback=True, config=sales_date_factory.filter(), is_sales=True, state=SalesStates.SELECT_DATE)
async def sales_select_date(sender: Sender, state: StateContext):
    cb = sales_date_factory.parse(sender.msg.data)
    selected_date_str = cb['date']
    selected_date = date.fromisoformat(selected_date_str)

    await state.add_data(visit_date=selected_date_str)
    await state.set(SalesStates.SELECT_TIME_SLOT)

    slot_avail = await _build_slot_availability(selected_date)
    await sender.edit_text(
        f"✅ Sana: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n\n⏰ Vaqt oralig'ini tanlang:",
        markup=time_slot_keyboard_avail(slot_avail),
    )
    await sender.answer()


@handler(callback=True, call='sales:back_to_date', is_sales=True, state=SalesStates.SELECT_TIME_SLOT)
async def sales_back_to_date(sender: Sender, state: StateContext):
    await state.set(SalesStates.SELECT_DATE)
    date_avail = await _build_date_availability()
    await sender.edit_text("📅 Borish sanasini tanlang:", markup=date_picker_keyboard(date_avail))
    await sender.answer()


# ── Step 8: Time slot selection ────────────────────────────────────────────────

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

    async with state.data() as data:
        visit_date = date.fromisoformat(data['visit_date'])

    free_agros = await _get_free_agronomists(visit_date, slot_value)
    if not free_agros:
        await sender.answer("❌ Bu vaqtda hech qanday agronom bo'sh emas!", show_alert=True)
        return

    await state.add_data(time_slot=slot_value, time_slot_label=slot_label)
    await state.set(SalesStates.SELECT_AGRONOMIST)

    await sender.edit_text(
        f"✅ Vaqt: <b>{slot_label}</b>\n\n🌱 Agronomni tanlang:",
        markup=agronomist_list_keyboard(free_agros),
    )
    await sender.answer()


@handler(callback=True, call='sales:back_to_slot', is_sales=True, state=SalesStates.SELECT_AGRONOMIST)
async def sales_back_to_slot(sender: Sender, state: StateContext):
    await state.set(SalesStates.SELECT_TIME_SLOT)
    async with state.data() as data:
        visit_date = date.fromisoformat(data['visit_date'])
    slot_avail = await _build_slot_availability(visit_date)
    await sender.edit_text(
        f"✅ Sana: <b>{visit_date.strftime('%d.%m.%Y')}</b>\n\n⏰ Vaqt oralig'ini tanlang:",
        markup=time_slot_keyboard_avail(slot_avail),
    )
    await sender.answer()


# ── Step 9: Agronomist selection ───────────────────────────────────────────────

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
    await state.set(SalesStates.CONFIRM_ORDER)

    async with state.data() as data:
        visit_date_str = data.get('visit_date', '')
        slot_label = data.get('time_slot_label', '—')
        d = date.fromisoformat(visit_date_str) if visit_date_str else None
        date_display = d.strftime('%d.%m.%Y') if d else '—'
        summary = (
            f"📋 <b>Buyurtma ma'lumotlari:</b>\n\n"
            f"👤 Mijoz: {data.get('client_name')}\n"
            f"📞 Tel 1: {data.get('phone1')}\n"
            f"📞 Tel 2: {data.get('phone2') or '—'}\n"
            f"🌳 Daraxt: {data.get('tree_count')}\n"
            f"🔴 Muammo: {data.get('problem')}\n"
            f"📍 Manzil: {data.get('address')}\n"
            f"📅 Sana: {date_display}\n"
            f"⏰ Vaqt: {slot_label}\n"
            f"🌱 Agronom: {agro.full_name}"
        )

    await sender.edit_text(summary, markup=confirm_order_keyboard())
    await sender.answer()


# ── Step 10: Confirm ───────────────────────────────────────────────────────────

@handler(callback=True, config=order_confirm_factory.filter(), is_sales=True, state=SalesStates.CONFIRM_ORDER)
async def sales_confirm_order(sender: Sender, state: StateContext):
    cb = order_confirm_factory.parse(sender.msg.data)
    if cb['answer'] == 'no':
        await state.delete()
        await sender.edit_text("❌ Bekor qilindi.")
        await sender.text("Sotuvchi paneli:", markup=sales_main_menu())
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
        visit_date = date.fromisoformat(data['visit_date'])

    try:
        sales_user = await TelegramUser.objects.aget(telegram_id=sender.user_id)
        agro = await TelegramUser.objects.aget(pk=agro_id)

        client = None
        try:
            client = await TelegramUser.objects.aget(phone=phone1, role=UserRole.CLIENT)
        except TelegramUser.DoesNotExist:
            pass

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
            visit_date=visit_date,
            source=OrderSource.SALES_CREATED,
            status=initial_status,
        )
    except Exception as exc:
        logger.error("Order creation failed: %s", exc)
        await sender.edit_text("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
        await sender.text("Sotuvchi paneli:", markup=sales_main_menu())
        await sender.answer()
        return

    await state.delete()
    await sender.edit_text(f"✅ Buyurtma #{order.pk} muvaffaqiyatli yaratildi!")
    await sender.text("Sotuvchi paneli:", markup=sales_main_menu())
    await sender.answer(f"✅ Buyurtma #{order.pk} yaratildi!")

    if client and initial_status == OrderStatus.AWAITING_CLIENT:
        await _notify_client_for_confirmation(order, client)
    else:
        await _notify_order_created(order, agro)


# ── Availability helpers ───────────────────────────────────────────────────────

async def _build_date_availability() -> list:
    """Return list of (date_str, is_available) for next 30 days."""
    from django.utils import timezone
    today = timezone.now().date()
    total_agros = await TelegramUser.objects.filter(
        role=UserRole.AGRONOMIST, is_active=True
    ).acount()
    if total_agros == 0:
        return [(str(today + timedelta(days=i)), False) for i in range(1, 31)]

    start = today + timedelta(days=1)
    end = today + timedelta(days=31)

    busy: dict = {}
    async for row in Order.objects.filter(
        visit_date__gte=start,
        visit_date__lt=end,
        agronomist__isnull=False,
        status__in=[
            OrderStatus.PENDING, OrderStatus.APPROVED,
            OrderStatus.IN_PROGRESS, OrderStatus.AWAITING_CLIENT,
        ],
    ).values_list('visit_date', 'time_slot', 'agronomist_id').aiterator():
        vd, slot, agro_id = row
        busy.setdefault(vd, {}).setdefault(slot, set()).add(agro_id)

    slots = [v for v, _ in TimeSlot.choices]
    result = []
    for i in range(1, 31):
        d = today + timedelta(days=i)
        day_busy = busy.get(d, {})
        available = any(
            len(day_busy.get(slot, set())) < total_agros
            for slot in slots
        )
        result.append((str(d), available))
    return result


async def _build_slot_availability(visit_date: date) -> list:
    """Return list of (value, label, is_available) for given date."""
    total_agros = await TelegramUser.objects.filter(
        role=UserRole.AGRONOMIST, is_active=True
    ).acount()
    if total_agros == 0:
        return [(v, l, False) for v, l in TimeSlot.choices]

    busy: dict = {}
    async for row in Order.objects.filter(
        visit_date=visit_date,
        agronomist__isnull=False,
        status__in=[
            OrderStatus.PENDING, OrderStatus.APPROVED,
            OrderStatus.IN_PROGRESS, OrderStatus.AWAITING_CLIENT,
        ],
    ).values_list('time_slot', 'agronomist_id').aiterator():
        slot, agro_id = row
        busy.setdefault(slot, set()).add(agro_id)

    return [
        (v, l, len(busy.get(v, set())) < total_agros)
        for v, l in TimeSlot.choices
    ]


async def _get_free_agronomists(visit_date: date, slot: str) -> list:
    """Return agronomists who have no order on visit_date at the given slot."""
    busy_ids: set = set()
    async for agro_id in Order.objects.filter(
        visit_date=visit_date,
        time_slot=slot,
        agronomist__isnull=False,
        status__in=[
            OrderStatus.PENDING, OrderStatus.APPROVED,
            OrderStatus.IN_PROGRESS, OrderStatus.AWAITING_CLIENT,
        ],
    ).values_list('agronomist_id', flat=True).aiterator():
        if agro_id:
            busy_ids.add(agro_id)

    free = []
    async for agro in TelegramUser.objects.filter(
        role=UserRole.AGRONOMIST, is_active=True
    ).aiterator():
        if agro.pk not in busy_ids:
            free.append(agro)
    return free


# ── Accept client-created orders ───────────────────────────────────────────────

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

    order = await Order.objects.select_related('client', 'agronomist', 'sales_manager').aget(pk=order_id)
    await notify_admins(
        bot,
        f"🆕 Yangi buyurtma #{order.pk} (client tomonidan).\n\n" + format_order_card(order),
        reply_markup=approve_order_keyboard(order.pk),
    )

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


# ── Notification helpers ───────────────────────────────────────────────────────

async def _notify_client_for_confirmation(order: Order, client: TelegramUser):
    try:
        from bots.client_bot.loader import bot as client_bot
        from bots.client_bot.keyboards.client import order_notification_keyboard
        from core.i18n import t
        lang = client.language or 'uz'
        text = t('order_notification', lang,
                 order_id=order.pk,
                 order_card=format_order_card(order))
        await notify_user(client_bot, client.telegram_id, text,
                          reply_markup=order_notification_keyboard(order.pk, lang))
    except Exception as exc:
        logger.error("Failed to notify client %s: %s", client.telegram_id, exc)
        await Order.objects.filter(pk=order.pk).aupdate(status=OrderStatus.PENDING)
        agro = await TelegramUser.objects.aget(pk=order.agronomist_id)
        await _notify_order_created(order, agro)


async def _notify_order_created(order: Order, agro: TelegramUser):
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
