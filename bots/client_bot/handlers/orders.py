"""
Client bot order handlers — all navigation via inline callbacks.
Text input only for: problem, address, tree count, cancel reason, reject reason, comment.
"""
import logging
from telebot.states.asyncio.context import StateContext

from bots.client_bot.loader import bot, handler
from bots.client_bot.states import OrderStates, RatingStates
from bots.client_bot.keyboards.client import (
    main_menu_keyboard, orders_menu_keyboard, cancel_keyboard,
    confirm_order_keyboard, order_notification_keyboard,
    service_done_keyboard, rating_keyboard, skip_comment_keyboard,
)
from bots.base.sender import Sender
from core.callbacks import (
    client_accept_factory, client_reject_factory,
    client_confirm_factory, client_reject_service_factory,
    rate_factory,
)
from core.helpers import notify_user, format_order_card, format_order_card_lang
from core.locks import try_lock, release_lock
from core.i18n import t
from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order, OrderStatus, OrderSource, Feedback

logger = logging.getLogger(__name__)


async def _get_client(telegram_id: int) -> TelegramUser | None:
    try:
        return await TelegramUser.objects.aget(
            telegram_id=telegram_id, role=UserRole.CLIENT, is_active=True
        )
    except TelegramUser.DoesNotExist:
        return None


# ── Orders menu ───────────────────────────────────────────────────────────────

@handler(callback=True, call='menu:orders')
async def client_orders_menu(sender: Sender, state: StateContext):
    await state.delete()
    lang = sender.lang
    await sender.edit_text(t('orders_menu', lang), markup=orders_menu_keyboard(lang))
    await sender.answer()


@handler(callback=True, call='orders:back')
async def client_orders_back(sender: Sender, state: StateContext):
    lang = sender.lang
    await sender.edit_text(t('main_menu', lang), markup=main_menu_keyboard(lang))
    await sender.answer()


# ── Create order ──────────────────────────────────────────────────────────────

@handler(callback=True, call='orders:create')
async def client_create_order_start(sender: Sender, state: StateContext):
    lang = sender.lang
    client = await _get_client(sender.user_id)
    if not client:
        await sender.answer(t('error_not_registered', lang), show_alert=True)
        return
    if not client.phone:
        await sender.answer(t('invalid_phone', lang), show_alert=True)
        return

    await state.set(OrderStates.ENTER_PROBLEM)
    await state.add_data(client_lang=lang)
    await sender.edit_text(t('ask_problem', lang), markup=cancel_keyboard(lang))
    await sender.answer()


@handler(callback=True, call='client:cancel', state=[
    OrderStates.ENTER_PROBLEM, OrderStates.ENTER_ADDRESS,
    OrderStates.ENTER_TREE_COUNT, OrderStates.CONFIRM_ORDER,
    OrderStates.ENTER_CANCEL_REASON, OrderStates.ENTER_REJECT_REASON,
])
async def client_cancel_flow(sender: Sender, state: StateContext):
    async with state.data() as data:
        lang = data.get('client_lang', sender.lang)
    await state.delete()
    await sender.edit_text(t('order_cancelled_msg', lang))
    await sender.text(t('main_menu', lang), markup=main_menu_keyboard(lang))
    await sender.answer()


@handler(state=OrderStates.ENTER_PROBLEM)
async def client_enter_problem(sender: Sender, state: StateContext):
    async with state.data() as data:
        lang = data.get('client_lang', sender.lang)
    text = sender.msg.text.strip() if sender.msg.text else ''
    if len(text) < 5:
        await sender.text(t('problem_too_short', lang), markup=cancel_keyboard(lang))
        return
    await state.add_data(problem=text)
    await state.set(OrderStates.ENTER_ADDRESS)
    await sender.text(t('ask_address', lang), markup=cancel_keyboard(lang))


@handler(state=OrderStates.ENTER_ADDRESS)
async def client_enter_address(sender: Sender, state: StateContext):
    async with state.data() as data:
        lang = data.get('client_lang', sender.lang)
    text = sender.msg.text.strip() if sender.msg.text else ''
    if len(text) < 5:
        await sender.text(t('address_too_short', lang), markup=cancel_keyboard(lang))
        return
    await state.add_data(address=text)
    await state.set(OrderStates.ENTER_TREE_COUNT)
    await sender.text(t('ask_tree_count', lang), markup=cancel_keyboard(lang))


@handler(state=OrderStates.ENTER_TREE_COUNT, is_digit=True)
async def client_enter_tree_count(sender: Sender, state: StateContext):
    async with state.data() as data:
        lang = data.get('client_lang', sender.lang)
    count = int(sender.msg.text.strip())
    if count < 1:
        await sender.text(t('invalid_tree_count', lang), markup=cancel_keyboard(lang))
        return
    await state.add_data(tree_count=count)
    await state.set(OrderStates.CONFIRM_ORDER)

    client = await _get_client(sender.user_id)
    async with state.data() as data:
        summary = t('order_summary', lang,
                    problem=data.get('problem', ''),
                    address=data.get('address', ''),
                    tree_count=count,
                    phone=client.phone if client else '—')

    await sender.text(summary, markup=confirm_order_keyboard(lang))


@handler(state=OrderStates.ENTER_TREE_COUNT, is_digit=False)
async def client_tree_count_invalid(sender: Sender, state: StateContext):
    async with state.data() as data:
        lang = data.get('client_lang', sender.lang)
    await sender.text(t('invalid_tree_count', lang), markup=cancel_keyboard(lang))


@handler(callback=True, call='order:confirm', state=OrderStates.CONFIRM_ORDER)
async def client_confirm_new_order(sender: Sender, state: StateContext):
    async with state.data() as data:
        lang = data.get('client_lang', sender.lang)
        problem = data.get('problem', '')
        address = data.get('address', '')
        tree_count = data.get('tree_count', 0)

    client = await _get_client(sender.user_id)
    if not client:
        await sender.answer(t('error_not_registered', lang), show_alert=True)
        await state.delete()
        return

    try:
        order = await Order.objects.acreate(
            client=client,
            client_name=client.full_name,
            phone1=client.phone or '',
            tree_count=tree_count,
            problem=problem,
            address=address,
            source=OrderSource.CLIENT_CREATED,
            status=OrderStatus.AWAITING_SALES,
        )
    except Exception as exc:
        logger.error("Client order creation failed: %s", exc)
        await sender.answer(t('error_generic', lang), show_alert=True)
        return

    await state.delete()
    await sender.edit_text(t('order_sent', lang, order_id=order.pk))
    await sender.text(t('main_menu', lang), markup=main_menu_keyboard(lang))
    await sender.answer()

    await _notify_sales_new_client_order(order)


@handler(callback=True, call='order:cancel', state=OrderStates.CONFIRM_ORDER)
async def client_cancel_confirm(sender: Sender, state: StateContext):
    async with state.data() as data:
        lang = data.get('client_lang', sender.lang)
    await state.delete()
    await sender.edit_text(t('order_cancelled_msg', lang))
    await sender.text(t('main_menu', lang), markup=main_menu_keyboard(lang))
    await sender.answer()


async def _notify_sales_new_client_order(order: Order):
    from bots.main_bot.loader import bot as main_bot
    from bots.main_bot.keyboards.sales import client_order_accept_keyboard
    from core.helpers import notify_sales_managers
    card = (
        f"🆕 <b>Client buyurtmasi #{order.pk}</b>\n\n"
        f"👤 {order.client_name}\n"
        f"📞 {order.phone1}\n"
        f"🌳 {order.tree_count} daraxt\n"
        f"🔴 {order.problem}\n"
        f"📍 {order.address}"
    )
    try:
        await notify_sales_managers(main_bot, card,
                                    reply_markup=client_order_accept_keyboard(order.pk))
    except Exception as exc:
        logger.error("Failed to notify sales: %s", exc)


# ── View active orders ────────────────────────────────────────────────────────

ACTIVE_STATUSES = [
    OrderStatus.AWAITING_SALES, OrderStatus.AWAITING_CLIENT,
    OrderStatus.PENDING, OrderStatus.APPROVED, OrderStatus.IN_PROGRESS,
]


@handler(callback=True, call='orders:active')
async def client_active_orders(sender: Sender, state: StateContext):
    lang = sender.lang
    client = await _get_client(sender.user_id)
    if not client:
        await sender.answer(t('error_not_registered', lang), show_alert=True)
        return

    orders = []
    async for o in Order.objects.filter(
        client=client, status__in=ACTIVE_STATUSES,
    ).aiterator():
        orders.append(o)

    await sender.answer()
    if not orders:
        await sender.edit_text(t('no_active_orders', lang), markup=orders_menu_keyboard(lang))
        return

    await sender.edit_text(f"📦 {t('btn_active_orders', lang)}:")
    for order in orders:
        await bot.send_message(
            sender.chat_id,
            format_order_card_lang(order, lang),
            parse_mode='HTML',
        )


# ── Order history ─────────────────────────────────────────────────────────────

HISTORY_STATUSES = [
    OrderStatus.COMPLETED, OrderStatus.CANCELLED,
    OrderStatus.CLIENT_CONFIRMED, OrderStatus.CLIENT_REJECTED,
]


@handler(callback=True, call='orders:history')
async def client_order_history(sender: Sender, state: StateContext):
    lang = sender.lang
    client = await _get_client(sender.user_id)
    if not client:
        await sender.answer(t('error_not_registered', lang), show_alert=True)
        return

    orders = []
    async for o in Order.objects.filter(
        client=client, status__in=HISTORY_STATUSES,
    ).aiterator():
        orders.append(o)

    await sender.answer()
    if not orders:
        await sender.edit_text(t('no_order_history', lang), markup=orders_menu_keyboard(lang))
        return

    await sender.edit_text(f"📋 {t('btn_order_history', lang)}:")
    for order in orders[:10]:
        await bot.send_message(
            sender.chat_id,
            format_order_card_lang(order, lang),
            parse_mode='HTML',
        )


# ── Accept/reject sales-created order ────────────────────────────────────────

@handler(callback=True, config=client_accept_factory.filter())
async def client_accept_order(sender: Sender, state: StateContext):
    cb = client_accept_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])
    lang = sender.lang

    lock_key = f"client_accept:{order_id}"
    if not await try_lock(lock_key, ttl=10):
        await sender.answer("⏳", show_alert=False)
        return

    try:
        order = await Order.objects.select_related('agronomist', 'sales_manager').aget(
            pk=order_id, status=OrderStatus.AWAITING_CLIENT
        )
    except Order.DoesNotExist:
        await sender.answer(t('error_generic', lang), show_alert=True)
        await release_lock(lock_key)
        return

    client = await _get_client(sender.user_id)
    await Order.objects.filter(pk=order_id).aupdate(client=client, status=OrderStatus.PENDING)
    await release_lock(lock_key)

    await sender.edit_markup()
    await sender.text(t('order_accepted_msg', lang))
    await sender.answer(t('order_accepted_msg', lang))

    from bots.main_bot.loader import bot as main_bot
    from bots.main_bot.keyboards.admin import approve_order_keyboard
    order = await Order.objects.select_related('agronomist', 'sales_manager').aget(pk=order_id)

    if order.sales_manager_id:
        await notify_user(
            main_bot, order.sales_manager.telegram_id,
            f"✅ Mijoz buyurtma #{order_id}ni tasdiqladi.",
        )
    from core.helpers import notify_admins
    await notify_admins(
        main_bot,
        f"🆕 Yangi buyurtma #{order_id} (mijoz tasdiqladi).\n\n" + format_order_card(order),
        reply_markup=approve_order_keyboard(order_id),
    )


@handler(callback=True, config=client_reject_factory.filter())
async def client_reject_order(sender: Sender, state: StateContext):
    cb = client_reject_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])
    lang = sender.lang

    await state.set(OrderStates.ENTER_CANCEL_REASON)
    await state.add_data(rejecting_order_id=order_id, client_lang=lang)
    await sender.edit_markup()
    await sender.text(t('ask_cancel_reason', lang), markup=cancel_keyboard(lang))
    await sender.answer()


# ── Confirm/reject completed service ─────────────────────────────────────────

@handler(callback=True, config=client_confirm_factory.filter())
async def client_confirm_service(sender: Sender, state: StateContext):
    cb = client_confirm_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])
    lang = sender.lang

    lock_key = f"client_confirm:{order_id}"
    if not await try_lock(lock_key, ttl=10):
        await sender.answer("⏳", show_alert=False)
        return

    try:
        order = await Order.objects.select_related('agronomist', 'sales_manager').aget(
            pk=order_id, status=OrderStatus.COMPLETED
        )
    except Order.DoesNotExist:
        await sender.answer(t('error_generic', lang), show_alert=True)
        await release_lock(lock_key)
        return

    await Order.objects.filter(pk=order_id).aupdate(status=OrderStatus.CLIENT_CONFIRMED)
    await release_lock(lock_key)

    await sender.edit_markup()
    await sender.text(t('service_confirmed_msg', lang), markup=rating_keyboard(order_id))
    await sender.answer()

    from bots.main_bot.loader import bot as main_bot
    if order.agronomist_id:
        await notify_user(main_bot, order.agronomist.telegram_id,
                          f"✅ Mijoz buyurtma #{order_id}ni tasdiqladi! Rahmat!")
    if order.sales_manager_id:
        await notify_user(main_bot, order.sales_manager.telegram_id,
                          f"✅ Buyurtma #{order_id} mijoz tomonidan tasdiqlandi.")
    from core.helpers import notify_admins
    await notify_admins(main_bot, f"✅ Buyurtma #{order_id} mijoz tomonidan tasdiqlandi.")


@handler(callback=True, config=client_reject_service_factory.filter())
async def client_reject_service(sender: Sender, state: StateContext):
    cb = client_reject_service_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])
    lang = sender.lang

    await state.set(OrderStates.ENTER_REJECT_REASON)
    await state.add_data(rejecting_order_id=order_id, client_lang=lang)
    await sender.edit_markup()
    await sender.text(t('ask_reject_reason', lang), markup=cancel_keyboard(lang))
    await sender.answer()


# ── Rating ────────────────────────────────────────────────────────────────────

@handler(callback=True, config=rate_factory.filter())
async def client_rate(sender: Sender, state: StateContext):
    cb = rate_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])
    rating = int(cb['rating'])
    lang = sender.lang

    await state.set(RatingStates.ENTER_COMMENT)
    await state.add_data(rating_order_id=order_id, rating=rating, client_lang=lang)
    await sender.edit_markup()
    await sender.text(t('ask_comment', lang), markup=skip_comment_keyboard(lang))
    await sender.answer()


@handler(callback=True, call='comment:skip')
async def client_skip_comment(sender: Sender, state: StateContext):
    async with state.data() as data:
        order_id = data.get('rating_order_id')
        rating = data.get('rating', 5)
        lang = data.get('client_lang', sender.lang)

    await state.delete()
    if order_id:
        client = await _get_client(sender.user_id)
        await _save_feedback(order_id, client, rating, None)

    stars = '⭐' * rating
    await sender.edit_text(t('rated_msg', lang, stars=stars))
    await sender.text(t('main_menu', lang), markup=main_menu_keyboard(lang))
    await sender.answer()


async def _save_feedback(order_id: int, client, rating: int, comment: str | None):
    try:
        await Feedback.objects.aupdate_or_create(
            order_id=order_id,
            defaults={'client': client, 'rating': rating, 'comment': comment},
        )
    except Exception as exc:
        logger.error("Feedback save failed: %s", exc)
