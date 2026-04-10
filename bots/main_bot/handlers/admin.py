"""
Admin bot handlers — full admin control panel.
"""
import logging
from telebot.states.asyncio.context import StateContext

from bots.main_bot.loader import bot, handler
from bots.main_bot.states import AdminStates
from bots.main_bot.keyboards.admin import (
    admin_main_menu, user_management_keyboard, orders_menu_keyboard,
    notify_menu_keyboard, approve_order_keyboard, user_remove_keyboard,
    confirm_broadcast_keyboard, cancel_keyboard, view_order_keyboard,
)
from bots.base.sender import Sender
from core.callbacks import (
    admin_remove_factory, admin_approve_factory,
    admin_cancel_order_factory, admin_view_order_factory,
)
from core.helpers import notify_user, notify_admins, broadcast, format_order_card
from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order, OrderStatus, TreatmentDetails
from django.utils import timezone

logger = logging.getLogger(__name__)

ADMIN_WELCOME = (
    "👑 <b>Admin paneli</b>\n\n"
    "Xush kelibsiz, {name}!"
)


# ── /start ────────────────────────────────────────────────────────────────────

@handler(commands=['start'], is_admin=True)
async def admin_start(sender: Sender, state: StateContext):
    await state.delete()
    user = await TelegramUser.objects.aget(telegram_id=sender.user_id)
    await sender.text(
        ADMIN_WELCOME.format(name=user.full_name),
        markup=admin_main_menu(),
    )


# ── Main menu navigation ──────────────────────────────────────────────────────

@handler(callback=True, call='admin:users', is_admin=True)
async def admin_users_menu(sender: Sender, state: StateContext):
    await state.delete()
    await sender.edit_text("👥 <b>Foydalanuvchilar</b>", markup=user_management_keyboard())
    await sender.answer()


@handler(callback=True, call='admin:orders', is_admin=True)
async def admin_orders_menu(sender: Sender, state: StateContext):
    await state.delete()
    await sender.edit_text("📦 <b>Buyurtmalar</b>", markup=orders_menu_keyboard())
    await sender.answer()


@handler(callback=True, call='admin:notify', is_admin=True)
async def admin_notify_menu(sender: Sender, state: StateContext):
    await state.delete()
    await sender.edit_text("📢 <b>Xabar yuborish</b>", markup=notify_menu_keyboard())
    await sender.answer()


@handler(callback=True, call='admin:back_main', is_admin=True)
async def admin_back_main(sender: Sender, state: StateContext):
    await state.delete()
    await sender.edit_text("👑 <b>Admin paneli</b>", markup=admin_main_menu())
    await sender.answer()


@handler(callback=True, call='cancel_flow', is_admin=True)
async def admin_cancel_flow(sender: Sender, state: StateContext):
    await state.delete()
    await sender.text("❌ Bekor qilindi.", markup=admin_main_menu())
    await sender.answer()


# ── Add Staff ─────────────────────────────────────────────────────────────────

@handler(callback=True, call='admin:add_manager', is_admin=True)
async def admin_add_manager_start(sender: Sender, state: StateContext):
    await state.set(AdminStates.ADD_MANAGER_ID)
    await sender.edit_text("📝 Sotuvchining Telegram ID sini kiriting:")
    await sender.answer()


@handler(callback=True, call='admin:add_agronomist', is_admin=True)
async def admin_add_agronomist_start(sender: Sender, state: StateContext):
    await state.set(AdminStates.ADD_AGRONOMIST_ID)
    await sender.edit_text("📝 Agronomning Telegram ID sini kiriting:")
    await sender.answer()


# ── List staff ────────────────────────────────────────────────────────────────

@handler(callback=True, call='admin:list_managers', is_admin=True)
async def admin_list_managers(sender: Sender, state: StateContext):
    lines = []
    async for u in TelegramUser.objects.filter(role=UserRole.SALES_MANAGER, is_active=True).aiterator():
        lines.append(f"• {u.full_name} (@{u.username or u.telegram_id})")
    text = "👥 <b>Sotuvchilar:</b>\n\n" + ("\n".join(lines) if lines else "— Yo'q")
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(row_width=1)
    async for u in TelegramUser.objects.filter(role=UserRole.SALES_MANAGER, is_active=True).aiterator():
        kb.add(InlineKeyboardButton(
            f"🗑 {u.full_name}",
            callback_data=admin_remove_factory.new(user_pk=u.pk),
        ))
    kb.add(InlineKeyboardButton("⬅️ Orqaga", callback_data="admin:users"))
    await sender.edit_text(text, markup=kb)
    await sender.answer()


@handler(callback=True, call='admin:list_agronomists', is_admin=True)
async def admin_list_agronomists(sender: Sender, state: StateContext):
    lines = []
    async for u in TelegramUser.objects.filter(role=UserRole.AGRONOMIST, is_active=True).aiterator():
        lines.append(f"• {u.full_name} (@{u.username or u.telegram_id})")
    text = "🌱 <b>Agronomlar:</b>\n\n" + ("\n".join(lines) if lines else "— Yo'q")
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(row_width=1)
    async for u in TelegramUser.objects.filter(role=UserRole.AGRONOMIST, is_active=True).aiterator():
        kb.add(InlineKeyboardButton(
            f"🗑 {u.full_name}",
            callback_data=admin_remove_factory.new(user_pk=u.pk),
        ))
    kb.add(InlineKeyboardButton("⬅️ Orqaga", callback_data="admin:users"))
    await sender.edit_text(text, markup=kb)
    await sender.answer()


@handler(callback=True, config=admin_remove_factory.filter(), is_admin=True)
async def admin_remove_user(sender: Sender, state: StateContext):
    cb = admin_remove_factory.parse(sender.msg.data)
    try:
        await TelegramUser.objects.filter(pk=int(cb['user_pk'])).aupdate(is_active=False)
        await sender.answer("✅ O'chirildi", show_alert=True)
        await sender.edit_text("✅ Foydalanuvchi o'chirildi.")
    except Exception as exc:
        logger.error("admin_remove_user: %s", exc)
        await sender.answer("❌ Xatolik", show_alert=True)


# ── View orders by status ─────────────────────────────────────────────────────

async def _show_orders_by_status(sender: Sender, status: str, title: str):
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    orders = []
    qs = Order.objects.filter(status=status).select_related('sales_manager', 'agronomist', 'client')
    async for o in qs.aiterator():
        orders.append(o)

    if not orders:
        await sender.edit_text(f"{title}\n\n📭 Buyurtmalar yo'q.")
        await sender.answer()
        return

    for order in orders[:10]:
        kb = InlineKeyboardMarkup(row_width=2)
        if status == OrderStatus.PENDING:
            kb.add(
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=admin_approve_factory.new(order_id=order.pk)),
                InlineKeyboardButton("❌ Bekor", callback_data=admin_cancel_order_factory.new(order_id=order.pk)),
            )
        await bot.send_message(
            sender.chat_id,
            format_order_card(order),
            reply_markup=kb if status == OrderStatus.PENDING else None,
        )

    await sender.answer()



@handler(callback=True, call='admin:orders_awaiting_sales', is_admin=True)
async def admin_orders_awaiting_sales(sender: Sender, state: StateContext):
    await _show_orders_by_status(sender, OrderStatus.AWAITING_SALES, "🆕 <b>Client so'rovlari</b>")


@handler(callback=True, call='admin:orders_pending', is_admin=True)
async def admin_orders_pending(sender: Sender, state: StateContext):
    await _show_orders_by_status(sender, OrderStatus.PENDING, "⏳ <b>Tasdiqlash kutilmoqda</b>")


@handler(callback=True, call='admin:orders_approved', is_admin=True)
async def admin_orders_approved(sender: Sender, state: StateContext):
    await _show_orders_by_status(sender, OrderStatus.APPROVED, "✅ <b>Tasdiqlangan</b>")


@handler(callback=True, call='admin:orders_inprogress', is_admin=True)
async def admin_orders_inprogress(sender: Sender, state: StateContext):
    await _show_orders_by_status(sender, OrderStatus.IN_PROGRESS, "🔄 <b>Jarayonda</b>")


@handler(callback=True, call='admin:orders_completed', is_admin=True)
async def admin_orders_completed(sender: Sender, state: StateContext):
    await _show_orders_by_status(sender, OrderStatus.COMPLETED, "✅ <b>Bajarilgan</b>")


@handler(callback=True, call='admin:orders_cancelled', is_admin=True)
async def admin_orders_cancelled(sender: Sender, state: StateContext):
    await _show_orders_by_status(sender, OrderStatus.CANCELLED, "❌ <b>Bekor qilingan</b>")


@handler(callback=True, call='admin:orders_retreatment', is_admin=True)
async def admin_orders_retreatment(sender: Sender, state: StateContext):
    today = timezone.now().date()
    lines = []
    async for td in TreatmentDetails.objects.filter(
        re_treatment_needed=True,
        re_treatment_date__gte=today,
    ).select_related('order').aiterator():
        lines.append(
            f"• Buyurtma #{td.order_id} — {td.order.client_name} | "
            f"📅 {td.re_treatment_date}"
        )
    text = "🔁 <b>Qayta ishlov:</b>\n\n" + ("\n".join(lines) if lines else "📭 Yo'q")
    await sender.edit_text(text, markup=orders_menu_keyboard())
    await sender.answer()


# ── Approve / Cancel order ────────────────────────────────────────────────────

@handler(callback=True, config=admin_approve_factory.filter(), is_admin=True)
async def admin_approve_order(sender: Sender, state: StateContext):
    cb = admin_approve_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])
    try:
        order = await Order.objects.select_related('agronomist', 'sales_manager', 'client').aget(pk=order_id)
    except Order.DoesNotExist:
        await sender.answer("❌ Buyurtma topilmadi", show_alert=True)
        return

    if order.status != OrderStatus.PENDING:
        await sender.answer("⚠️ Bu buyurtma allaqachon tasdiqlangan yoki bekor qilingan.", show_alert=True)
        return

    await Order.objects.filter(pk=order_id).aupdate(status=OrderStatus.APPROVED)

    await sender.edit_text(f"✅ Buyurtma #{order_id} tasdiqlandi!")
    await sender.answer("✅ Tasdiqlandi!")

    from bots.main_bot.keyboards.agronomist import order_actions_keyboard
    if order.agronomist_id:
        await notify_user(
            bot, order.agronomist.telegram_id,
            f"✅ <b>Buyurtma #{order_id} tasdiqlandi!</b>\n\n" + format_order_card(order),
            reply_markup=order_actions_keyboard(order_id),
        )
    if order.sales_manager_id:
        await notify_user(
            bot, order.sales_manager.telegram_id,
            f"✅ Buyurtma #{order_id} admin tomonidan tasdiqlandi.",
        )


@handler(callback=True, config=admin_cancel_order_factory.filter(), is_admin=True)
async def admin_cancel_order(sender: Sender, state: StateContext):
    cb = admin_cancel_order_factory.parse(sender.msg.data)
    order_id = int(cb['order_id'])
    try:
        order = await Order.objects.select_related('agronomist', 'sales_manager', 'client').aget(pk=order_id)
    except Order.DoesNotExist:
        await sender.answer("❌ Topilmadi", show_alert=True)
        return

    await Order.objects.filter(pk=order_id).aupdate(
        status=OrderStatus.CANCELLED,
        cancel_reason="Admin tomonidan bekor qilindi",
    )
    await sender.edit_text(f"❌ Buyurtma #{order_id} bekor qilindi.")
    await sender.answer("❌ Bekor qilindi!")

    if order.agronomist_id:
        await notify_user(bot, order.agronomist.telegram_id, f"❌ Buyurtma #{order_id} admin tomonidan bekor qilindi.")
    if order.sales_manager_id:
        await notify_user(bot, order.sales_manager.telegram_id, f"❌ Buyurtma #{order_id} admin tomonidan bekor qilindi.")


# ── Statistics ────────────────────────────────────────────────────────────────

@handler(callback=True, call='admin:stats', is_admin=True)
async def admin_stats(sender: Sender, state: StateContext):
    from django.db.models import Count, Avg

    total = await Order.objects.acount()

    counts = {}
    for status in OrderStatus.values:
        counts[status] = await Order.objects.filter(status=status).acount()

    avg_rating_result = await __import__('apps.orders.models', fromlist=['Feedback']).Feedback.objects.aaggregate(avg=Avg('rating'))
    avg_rating = avg_rating_result['avg']

    staff_count = await TelegramUser.objects.filter(
        role__in=[UserRole.SALES_MANAGER, UserRole.AGRONOMIST],
        is_active=True,
    ).acount()
    client_count = await TelegramUser.objects.filter(role=UserRole.CLIENT, is_active=True).acount()

    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"📦 Jami buyurtmalar: {total}\n"
        f"⏳ Sotuvchi kutmoqda: {counts.get('awaiting_sales', 0)}\n"
        f"🕐 Admin kutmoqda: {counts.get('pending', 0)}\n"
        f"✅ Tasdiqlangan: {counts.get('approved', 0)}\n"
        f"🔄 Jarayonda: {counts.get('in_progress', 0)}\n"
        f"✅ Bajarilgan: {counts.get('completed', 0)}\n"
        f"❌ Bekor qilingan: {counts.get('cancelled', 0)}\n"
        f"⭐ O'rtacha baho: {f'{avg_rating:.1f}' if avg_rating else '—'}\n\n"
        f"👥 Xodimlar: {staff_count}\n"
        f"👤 Mijozlar: {client_count}"
    )
    await sender.edit_text(text, markup=admin_main_menu())
    await sender.answer()


# ── Broadcast ─────────────────────────────────────────────────────────────────

@handler(callback=True, call='admin:broadcast', is_admin=True)
async def admin_broadcast_start(sender: Sender, state: StateContext):
    await state.set(AdminStates.BROADCAST_TEXT)
    await sender.edit_text("📢 Barcha foydalanuvchilarga xabar matnini kiriting:")
    await sender.answer()


@handler(callback=True, call='broadcast:confirm', is_admin=True)
async def admin_broadcast_confirm(sender: Sender, state: StateContext):
    async with state.data() as data:
        text = data.get('broadcast_text', '')
    if not text:
        await sender.answer("❌ Matn yo'q", show_alert=True)
        return
    await state.delete()
    await sender.edit_text("⏳ Yuborilmoqda...")
    count = await broadcast(bot, text)
    await sender.text(f"✅ {count} ta foydalanuvchiga yuborildi.", markup=admin_main_menu())


@handler(callback=True, call='broadcast:cancel', is_admin=True)
async def admin_broadcast_cancel(sender: Sender, state: StateContext):
    await state.delete()
    await sender.edit_text("❌ Bekor qilindi.", markup=admin_main_menu())
    await sender.answer()


# ── Message single user ───────────────────────────────────────────────────────

@handler(callback=True, call='admin:msg_user', is_admin=True)
async def admin_msg_user_start(sender: Sender, state: StateContext):
    await state.set(AdminStates.SEND_MESSAGE_SELECT_USER)
    await sender.edit_text("📩 Telegram ID kiriting:")
    await sender.answer()
