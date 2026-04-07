"""
Super Admin flow:
  User management | Order control | Notifications | Analytics
"""
import logging
from telebot import types
from telebot.states.asyncio.context import StateContext

from bot.loader import bot
from bot.states import AdminStates, AdminAddSalesManager
from bot.utils.state_manager import StateManager
from bot.utils.helpers import notify_user, notify_admins, broadcast, format_order_card
from bot.keyboards.admin_kb import (
    admin_main_menu, user_management_keyboard, orders_menu_keyboard,
    notifications_menu_keyboard, approve_order_keyboard,
    user_remove_keyboard, confirm_broadcast_keyboard, back_keyboard,
)
from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order, OrderStatus, TreatmentDetails, Feedback

logger = logging.getLogger(__name__)


async def _is_admin(telegram_id: int) -> bool:
    try:
        user = await TelegramUser.objects.aget(telegram_id=telegram_id, is_active=True)
        return user.role == UserRole.SUPER_ADMIN
    except TelegramUser.DoesNotExist:
        return False


# ── Main menu buttons ─────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data == "users")
async def admin_users_menu(call: types.CallbackQuery):
    if not await _is_admin(call.from_user.id):
        return
    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await bot.send_message(
        call.message.chat.id,
        "👥 <b>Foydalanuvchilar boshqaruvi:</b>",
        reply_markup=user_management_keyboard(),
    )


@bot.message_handler(func=lambda m: m.text == "📦 Buyurtmalar")
async def admin_orders_menu(message: types.Message):
    if not await _is_admin(message.from_user.id):
        return
    await bot.send_message(
        message.chat.id,
        "📦 <b>Buyurtmalar:</b>",
        reply_markup=orders_menu_keyboard(),
    )


@bot.message_handler(func=lambda m: m.text == "📢 Xabar yuborish")
async def admin_notifications_menu(message: types.Message):
    if not await _is_admin(message.from_user.id):
        return
    await bot.send_message(
        message.chat.id,
        "📢 <b>Xabar yuborish:</b>",
        reply_markup=notifications_menu_keyboard(),
    )


@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
async def admin_statistics(message: types.Message):
    if not await _is_admin(message.from_user.id):
        return
    await _send_statistics(message.chat.id)


@bot.message_handler(func=lambda m: m.text == "⬅️ Orqaga")
async def admin_back(message: types.Message):
    if not await _is_admin(message.from_user.id):
        return
    await StateManager.clear(message.from_user.id)
    await bot.send_message(message.chat.id, "🏠 Bosh menyu:", reply_markup=admin_main_menu())


# ── Statistics ────────────────────────────────────────────────────────────────

async def _send_statistics(chat_id: int):
    from django.db.models import Count, Avg
    from asgiref.sync import sync_to_async

    @sync_to_async
    def _fetch():
        total = Order.objects.count()
        by_status = dict(Order.objects.values_list('status').annotate(c=Count('id')))
        completed = by_status.get('completed', 0) + by_status.get('client_confirmed', 0)
        cancelled = by_status.get('cancelled', 0) + by_status.get('client_rejected', 0)
        pending = by_status.get('pending', 0)
        approved = by_status.get('approved', 0)
        in_prog = by_status.get('in_progress', 0)

        avg_rating = Feedback.objects.aggregate(avg=Avg('rating'))['avg'] or 0
        retreatments = TreatmentDetails.objects.filter(re_treatment_needed=True).count()
        total_managers = TelegramUser.objects.filter(role='sales_manager', is_active=True).count()
        total_agros = TelegramUser.objects.filter(role='agronomist', is_active=True).count()
        total_clients = TelegramUser.objects.filter(role='client', is_active=True).count()

        return (total, completed, cancelled, pending, approved, in_prog,
                avg_rating, retreatments, total_managers, total_agros, total_clients)

    (total, completed, cancelled, pending, approved, in_prog,
     avg_rating, retreatments, total_managers, total_agros, total_clients) = await _fetch()

    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"<b>Buyurtmalar:</b>\n"
        f"  Jami: {total}\n"
        f"  Yangi: {pending}\n"
        f"  Tasdiqlangan: {approved}\n"
        f"  Bajarilmoqda: {in_prog}\n"
        f"  Yakunlangan: {completed}\n"
        f"  Bekor qilingan: {cancelled}\n"
        f"  Qayta ishlov: {retreatments}\n\n"
        f"<b>Foydalanuvchilar:</b>\n"
        f"  Sotuvchilar: {total_managers}\n"
        f"  Agronomlar: {total_agros}\n"
        f"  Mijozlar: {total_clients}\n\n"
        f"<b>O'rtacha reyting:</b> {'⭐' * round(avg_rating)} ({avg_rating:.1f})"
    )
    await bot.send_message(chat_id, text)


# ── User management callbacks ─────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "admin:add_manager")
async def admin_cb_add_manager(call: types.CallbackQuery, state: StateContext):
    if not await _is_admin(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return
    await state.set(AdminAddSalesManager.tg_id)
    await bot.send_message(
        call.message.chat.id,
        "👤 Yangi sotuvchining <b>Telegram ID</b>sini kiriting:",
        reply_markup=back_keyboard(),
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin:add_agronomist")
async def admin_cb_add_agronomist(call: types.CallbackQuery):
    if not await _is_admin(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return
    await StateManager.set_state(call.from_user.id, AdminStates.ADD_AGRONOMIST_TELEGRAM_ID)
    await bot.send_message(
        call.message.chat.id,
        "🌱 Yangi agronomning <b>Telegram ID</b>sini kiriting:",
        reply_markup=back_keyboard(),
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin:list_managers")
async def admin_cb_list_managers(call: types.CallbackQuery):
    if not await _is_admin(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return
    await _list_role_users(call.message.chat.id, UserRole.SALES_MANAGER, "👥 Sotuvchilar")
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin:list_agronomists")
async def admin_cb_list_agronomists(call: types.CallbackQuery):
    if not await _is_admin(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return
    await _list_role_users(call.message.chat.id, UserRole.AGRONOMIST, "🌱 Agronomlar")
    await bot.answer_callback_query(call.id)


async def _list_role_users(chat_id: int, role: str, title: str):
    users = [u async for u in TelegramUser.objects.filter(role=role, is_active=True).aiterator()]
    if not users:
        await bot.send_message(chat_id, f"{title}: hali yo'q.")
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for u in users:
        kb.add(types.InlineKeyboardButton(
            f"{'❌'} {u.full_name} (ID: {u.telegram_id})",
            callback_data=f"admin:remove_user:{u.pk}"
        ))
    await bot.send_message(chat_id, f"<b>{title} ({len(users)} ta):</b>", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data.startswith("admin:remove_user:"))
async def admin_cb_remove_user(call: types.CallbackQuery):
    if not await _is_admin(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return
    user_pk = int(call.data.split(":")[2])
    try:
        user = await TelegramUser.objects.aget(pk=user_pk)
        user.is_active = False
        await user.asave(update_fields=['is_active', 'updated_at'])
        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        await bot.send_message(
            call.message.chat.id,
            f"✅ {user.full_name} o'chirildi (deaktivlashtirildi)."
        )
    except TelegramUser.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Foydalanuvchi topilmadi")
        return
    await bot.answer_callback_query(call.id)


# ── Order management callbacks ────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin:orders_"))
async def admin_cb_orders_filter(call: types.CallbackQuery):
    if not await _is_admin(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    filter_map = {
        'admin:orders_pending':     (OrderStatus.PENDING, "🆕 Yangi buyurtmalar"),
        'admin:orders_approved':    (OrderStatus.APPROVED, "✅ Tasdiqlangan"),
        'admin:orders_inprogress':  (OrderStatus.IN_PROGRESS, "🔄 Bajarilmoqda"),
        'admin:orders_completed':   (OrderStatus.COMPLETED, "🏁 Yakunlangan"),
        'admin:orders_cancelled':   (OrderStatus.CANCELLED, "❌ Bekor qilingan"),
    }

    if call.data == 'admin:orders_retreatment':
        await _list_retreatment_orders(call.message.chat.id)
        await bot.answer_callback_query(call.id)
        return

    if call.data not in filter_map:
        await bot.answer_callback_query(call.id)
        return

    status, title = filter_map[call.data]
    orders = [o async for o in Order.objects.filter(status=status).order_by('-created_at').aiterator()]

    if not orders:
        await bot.send_message(call.message.chat.id, f"{title}: hozircha yo'q.")
        await bot.answer_callback_query(call.id)
        return

    await bot.send_message(call.message.chat.id, f"<b>{title} ({len(orders)} ta):</b>")
    for order in orders[:15]:
        text = format_order_card(order)
        if status == OrderStatus.PENDING:
            await bot.send_message(
                call.message.chat.id, text,
                reply_markup=approve_order_keyboard(order.pk)
            )
        else:
            await bot.send_message(call.message.chat.id, text)
    await bot.answer_callback_query(call.id)


async def _list_retreatment_orders(chat_id: int):
    from datetime import date
    details = [
        d async for d in TreatmentDetails.objects.select_related('order').filter(
            re_treatment_needed=True,
            re_treatment_date__gte=date.today(),
        ).order_by('re_treatment_date').aiterator()
    ]
    if not details:
        await bot.send_message(chat_id, "🔁 Qayta ishlov jadvalida buyurtma yo'q.")
        return
    text = "🔁 <b>Qayta ishlov jadvali:</b>\n\n"
    for d in details[:20]:
        order = d.order
        text += (
            f"• #{order.pk} — {order.client_name}\n"
            f"  📅 Sana: {d.re_treatment_date}\n"
            f"  📍 {order.address}\n\n"
        )
    await bot.send_message(chat_id, text)


@bot.callback_query_handler(func=lambda c: c.data.startswith("admin:approve:"))
async def admin_cb_approve_order(call: types.CallbackQuery):
    if not await _is_admin(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    order_id = int(call.data.split(":")[2])
    try:
        order = await Order.objects.select_related('agronomist', 'sales_manager').aget(pk=order_id)
    except Order.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Buyurtma topilmadi")
        return

    if order.status != OrderStatus.PENDING:
        await bot.answer_callback_query(call.id, f"⚠️ Holat: {order.get_status_display()}")
        return

    order.status = OrderStatus.APPROVED
    await order.asave(update_fields=['status', 'updated_at'])

    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    await bot.send_message(call.message.chat.id, f"✅ Buyurtma #{order_id} tasdiqlandi!")

    from bot.keyboards.agronomist_kb import order_actions_keyboard
    agro_text = f"✅ <b>Buyurtma #{order_id} tasdiqlandi!</b>\n\n" + format_order_card(order)
    await notify_user(bot, order.agronomist.telegram_id, agro_text, reply_markup=order_actions_keyboard(order_id))
    await notify_user(bot, order.sales_manager.telegram_id, f"✅ Buyurtma #{order_id} admin tomonidan tasdiqlandi.")
    await bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")


@bot.callback_query_handler(func=lambda c: c.data.startswith("admin:cancel_order:"))
async def admin_cb_cancel_order(call: types.CallbackQuery):
    if not await _is_admin(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    order_id = int(call.data.split(":")[2])
    try:
        order = await Order.objects.select_related('agronomist', 'sales_manager').aget(pk=order_id)
    except Order.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Buyurtma topilmadi")
        return

    order.status = OrderStatus.CANCELLED
    order.cancel_reason = "Admin tomonidan bekor qilindi"
    await order.asave(update_fields=['status', 'cancel_reason', 'updated_at'])

    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    await bot.send_message(call.message.chat.id, f"❌ Buyurtma #{order_id} bekor qilindi.")

    cancel_text = f"❌ Buyurtma #{order_id} admin tomonidan bekor qilindi."
    await notify_user(bot, order.agronomist.telegram_id, cancel_text)
    await notify_user(bot, order.sales_manager.telegram_id, cancel_text)
    await bot.answer_callback_query(call.id)


# ── Notifications callbacks ───────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "admin:msg_user")
async def admin_cb_msg_user(call: types.CallbackQuery):
    if not await _is_admin(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    await StateManager.set_state(call.from_user.id, AdminStates.SEND_MESSAGE_SELECT_USER)
    await bot.send_message(
        call.message.chat.id,
        "👤 Xabar yubormoqchi bo'lgan foydalanuvchining <b>Telegram ID</b>sini kiriting:",
        reply_markup=back_keyboard(),
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin:broadcast")
async def admin_cb_broadcast(call: types.CallbackQuery):
    if not await _is_admin(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    await StateManager.set_state(call.from_user.id, AdminStates.BROADCAST_TEXT)
    await bot.send_message(
        call.message.chat.id,
        "📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabarni yozing:",
        reply_markup=back_keyboard(),
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data in ("broadcast:confirm", "broadcast:cancel"))
async def admin_cb_broadcast_confirm(call: types.CallbackQuery):
    if not await _is_admin(call.from_user.id):
        await bot.answer_callback_query(call.id, "⛔ Ruxsat yo'q")
        return

    state, data = await StateManager.get_state_and_data(call.from_user.id)
    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

    if call.data == "broadcast:cancel" or state != AdminStates.CONFIRM_BROADCAST:
        await StateManager.clear(call.from_user.id)
        await bot.send_message(call.message.chat.id, "❌ Bekor qilindi.", reply_markup=admin_main_menu())
        await bot.answer_callback_query(call.id)
        return

    text = data.get('broadcast_text', '')
    await StateManager.clear(call.from_user.id)
    await bot.send_message(call.message.chat.id, "⏳ Yuborilmoqda...")

    count = await broadcast(bot, text)
    await bot.send_message(
        call.message.chat.id,
        f"✅ Xabar {count} ta foydalanuvchiga yuborildi.",
        reply_markup=admin_main_menu(),
    )
    await bot.answer_callback_query(call.id)


# ── Admin text input router ───────────────────────────────────────────────────

@bot.message_handler(func=lambda m: True, content_types=['text'], state=AdminAddSalesManager.tg_id)
async def admin_add_sales_manager(message: types.Message, state: StateContext):
    if not await _is_admin(message.from_user.id):
        return
    print(message)
    
    text = message.text.strip()
    tid = message.from_user.id

    # ── Add manager: get telegram_id ─────────────────────────────────────────
    if state == AdminStates.ADD_MANAGER_TELEGRAM_ID:
        await _handle_add_user(message, text, tid, UserRole.SALES_MANAGER, AdminStates.ADD_MANAGER_NAME)

    # ── Add manager: get name ─────────────────────────────────────────────────
    elif state == AdminStates.ADD_MANAGER_NAME:
        await _finalize_add_user(message, text, tid, UserRole.SALES_MANAGER, "sotuvchi")

    # ── Add agronomist: get telegram_id ───────────────────────────────────────
    elif state == AdminStates.ADD_AGRONOMIST_TELEGRAM_ID:
        await _handle_add_user(message, text, tid, UserRole.AGRONOMIST, AdminStates.ADD_AGRONOMIST_NAME)

    # ── Add agronomist: get name ──────────────────────────────────────────────
    elif state == AdminStates.ADD_AGRONOMIST_NAME:
        await _finalize_add_user(message, text, tid, UserRole.AGRONOMIST, "agronom")

    # ── Send message: get user telegram_id ───────────────────────────────────
    elif state == AdminStates.SEND_MESSAGE_SELECT_USER:
        if not text.lstrip('-').isdigit():
            await bot.send_message(message.chat.id, "⚠️ Telegram ID raqam bo'lishi kerak:")
            return
        target_tid = int(text)
        try:
            target = await TelegramUser.objects.aget(telegram_id=target_tid)
        except TelegramUser.DoesNotExist:
            await bot.send_message(message.chat.id, f"❌ ID {target_tid} ro'yxatda yo'q.")
            return
        await StateManager.set_state(tid, AdminStates.SEND_MESSAGE_TEXT, data={'target_id': target_tid})
        await bot.send_message(
            message.chat.id,
            f"✅ Qabul qiluvchi: <b>{target.full_name}</b>\n\nXabar matnini yozing:"
        )

    # ── Send message: send text ───────────────────────────────────────────────
    elif state == AdminStates.SEND_MESSAGE_TEXT:
        target_id = data.get('target_id')
        await StateManager.clear(tid)
        sent = await notify_user(bot, target_id, f"📩 <b>Admin xabari:</b>\n\n{text}")
        if sent:
            await bot.send_message(message.chat.id, "✅ Xabar yuborildi!", reply_markup=admin_main_menu())
        else:
            await bot.send_message(message.chat.id, "❌ Xabar yuborib bo'lmadi.", reply_markup=admin_main_menu())

    # ── Broadcast: collect text ───────────────────────────────────────────────
    elif state == AdminStates.BROADCAST_TEXT:
        await StateManager.set_state(tid, AdminStates.CONFIRM_BROADCAST, data={'broadcast_text': text})
        await bot.send_message(
            message.chat.id,
            f"📢 <b>Xabar:</b>\n\n{text}\n\n<i>Bu xabar BARCHA foydalanuvchilarga yuboriladi. Tasdiqlaysizmi?</i>",
            reply_markup=confirm_broadcast_keyboard(),
        )


async def _handle_add_user(message, text: str, admin_tid: int, role: str, next_state: str):
    if not text.lstrip('-').isdigit():
        await bot.send_message(message.chat.id, "⚠️ Telegram ID raqam bo'lishi kerak:")
        return
    target_tid = int(text)

    # Check if already exists
    try:
        existing = await TelegramUser.objects.aget(telegram_id=target_tid)
        if existing.role == role and existing.is_active:
            await bot.send_message(message.chat.id, f"⚠️ Bu foydalanuvchi allaqachon {existing.get_role_display()} sifatida ro'yxatda.")
            await StateManager.clear(admin_tid)
            return
    except TelegramUser.DoesNotExist:
        pass

    await StateManager.update_data(admin_tid, new_user_telegram_id=target_tid)
    await StateManager.set_state(admin_tid, next_state)
    await bot.send_message(message.chat.id, "✅ ID qabul qilindi.\n\nTo'liq ismini kiriting:")


async def _finalize_add_user(message, name: str, admin_tid: int, role: str, role_label: str):
    data = await StateManager.get_data(admin_tid)
    target_tid = data.get('new_user_telegram_id')

    if not target_tid:
        await StateManager.clear(admin_tid)
        await bot.send_message(message.chat.id, "❌ Xatolik. Qayta boshlang.", reply_markup=admin_main_menu())
        return

    user, created = await TelegramUser.objects.aupdate_or_create(
        telegram_id=target_tid,
        defaults={'full_name': name, 'role': role, 'is_active': True},
    )
    await StateManager.clear(admin_tid)

    action = "qo'shildi" if created else "yangilandi"
    await bot.send_message(
        message.chat.id,
        f"✅ {role_label.capitalize()} {action}:\n"
        f"Ism: {name}\n"
        f"Telegram ID: {target_tid}",
        reply_markup=admin_main_menu(),
    )

    # Welcome notification to the new staff member
    role_greet = {"sales_manager": "Sotuvchi", "agronomist": "Agronom"}.get(role, role_label)
    await notify_user(
        bot, target_tid,
        f"🎉 Tabriklaymiz, {name}!\n\n"
        f"Siz Oscar Agro tizimiga <b>{role_greet}</b> sifatida qo'shildingiz.\n"
        f"Boshlash uchun /start bosing."
    )
