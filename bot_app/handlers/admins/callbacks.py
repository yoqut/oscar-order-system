"""
Super Admin flow:
  User management | Order control | Notifications | Analytics

Bugs fixed vs original:
  - AdminAddSalesManager was imported but not defined → added to use_states.py
  - admin_orders_menu / notifications / stats were message_handler instead of callback_query_handler
  - admin_cb_approve_order / cancel_order checked wrong callback prefix (admin:approve: vs adm_approve:)
  - admin_cb_add_manager used pyTelegramBotAPI StateContext instead of StateManager
  - admin_add_sales_manager text router was registered for wrong state & had undefined `data` variable
  - debug print(message) statement removed
  - _list_role_users now uses admin_remove_factory for consistent callback parsing
"""
import logging
from telebot import types

from ...core.loader import bot
from ...core.use_states import AdminStates
from ...utils.state_manager import StateManager
from ...utils.helpers import notify_user, broadcast, format_order_card
from ...core.callback_factories import admin_remove_factory, admin_approve_factory, admin_cancel_order_factory
from ...keyboards.admin_kb import (
    approve_order_keyboard,
    confirm_broadcast_keyboard, back_keyboard, admin_main_menu,
)
from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order, OrderStatus, TreatmentDetails

logger = logging.getLogger(__name__)


# ── Main menu inline callbacks ────────────────────────────────────────────────


# Reply keyboard "Back" button
@bot.callback_query_handler(func=lambda call: call.data.startswith("back"), is_admin=True)
async def admin_back_cb(call: types.CallbackQuery):
    await bot.edit_message_text(
        "👥 <b>Foydalanuvchilar boshqaruvi:</b>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=admin_main_menu()
    )


@bot.message_handler(func=lambda m: m.text == "⬅️ Orqaga")
async def admin_back(message: types.Message):
    await StateManager.clear(message.from_user.id)
    await bot.send_message(message.chat.id, "🏠 Bosh menyu:", reply_markup=admin_main_menu())


# ── User management callbacks ─────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "admin:add_manager")
async def admin_cb_add_manager(call: types.CallbackQuery):
    await StateManager.set_state(call.from_user.id, AdminStates.ADD_MANAGER_TELEGRAM_ID)
    await bot.send_message(
        call.message.chat.id,
        "👤 Yangi sotuvchining <b>Telegram ID</b>sini kiriting:",
        reply_markup=back_keyboard(),
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin:add_agronomist")
async def admin_cb_add_agronomist(call: types.CallbackQuery):
    await StateManager.set_state(call.from_user.id, AdminStates.ADD_AGRONOMIST_TELEGRAM_ID)
    await bot.send_message(
        call.message.chat.id,
        "🌱 Yangi agronomning <b>Telegram ID</b>sini kiriting:",
        reply_markup=back_keyboard(),
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin:list_managers")
async def admin_cb_list_managers(call: types.CallbackQuery):
    await _list_role_users(call.message.chat.id, UserRole.SALES_MANAGER, "👥 Sotuvchilar")
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin:list_agronomists")
async def admin_cb_list_agronomists(call: types.CallbackQuery):
    await _list_role_users(call.message.chat.id, UserRole.AGRONOMIST, "🌱 Agronomlar")
    await bot.answer_callback_query(call.id)


async def _list_role_users(chat_id: int, role: str, title: str) -> None:
    users = [u async for u in TelegramUser.objects.filter(role=role, is_active=True).aiterator()]
    if not users:
        await bot.send_message(chat_id, f"{title}: hali yo'q.")
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for u in users:
        kb.add(types.InlineKeyboardButton(
            f"❌ {u.full_name} (ID: {u.telegram_id})",
            callback_data=admin_remove_factory.new(user_pk=u.pk),
        ))
    await bot.send_message(chat_id, f"<b>{title} ({len(users)} ta):</b>", reply_markup=kb)


@bot.callback_query_handler(func=None, config=admin_remove_factory.filter())
async def admin_cb_remove_user(call: types.CallbackQuery):
    cb = admin_remove_factory.parse(call.data)
    user_pk = int(cb['user_pk'])
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

    filter_map = {
        'admin:orders_pending':    (OrderStatus.PENDING,    "🆕 Yangi buyurtmalar"),
        'admin:orders_approved':   (OrderStatus.APPROVED,   "✅ Tasdiqlangan"),
        'admin:orders_inprogress': (OrderStatus.IN_PROGRESS,"🔄 Bajarilmoqda"),
        'admin:orders_completed':  (OrderStatus.COMPLETED,  "🏁 Yakunlangan"),
        'admin:orders_cancelled':  (OrderStatus.CANCELLED,  "❌ Bekor qilingan"),
    }

    if call.data == 'admin:orders_retreatment':
        await _list_retreatment_orders(call.message.chat.id)
        await bot.answer_callback_query(call.id)
        return

    if call.data not in filter_map:
        await bot.answer_callback_query(call.id)
        return

    status, title = filter_map[call.data]
    orders = [o async for o in
              Order.objects.filter(status=status).order_by('-created_at').aiterator()]

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
                reply_markup=approve_order_keyboard(order.pk),
            )
        else:
            await bot.send_message(call.message.chat.id, text)
    await bot.answer_callback_query(call.id)


async def _list_retreatment_orders(chat_id: int) -> None:
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


@bot.callback_query_handler(func=None, config=admin_approve_factory.filter())
async def admin_cb_approve_order(call: types.CallbackQuery):

    cb = admin_approve_factory.parse(call.data)
    order_id = int(cb['order_id'])
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

    from bot_app.keyboards.agronomist_kb import order_actions_keyboard
    agro_text = f"✅ <b>Buyurtma #{order_id} tasdiqlandi!</b>\n\n" + format_order_card(order)
    await notify_user(bot, order.agronomist.telegram_id, agro_text,
                      reply_markup=order_actions_keyboard(order_id))
    await notify_user(bot, order.sales_manager.telegram_id,
                      f"✅ Buyurtma #{order_id} admin tomonidan tasdiqlandi.")
    await bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")


@bot.callback_query_handler(func=None, config=admin_cancel_order_factory.filter())
async def admin_cb_cancel_order(call: types.CallbackQuery):
    cb = admin_cancel_order_factory.parse(call.data)
    order_id = int(cb['order_id'])
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
    await StateManager.set_state(call.from_user.id, AdminStates.SEND_MESSAGE_SELECT_USER)
    await bot.send_message(
        call.message.chat.id,
        "👤 Xabar yubormoqchi bo'lgan foydalanuvchining <b>Telegram ID</b>sini kiriting:",
        reply_markup=back_keyboard(),
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin:broadcast")
async def admin_cb_broadcast(call: types.CallbackQuery):

    await StateManager.set_state(call.from_user.id, AdminStates.BROADCAST_TEXT)
    await bot.send_message(
        call.message.chat.id,
        "📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabarni yozing:",
        reply_markup=back_keyboard(),
    )
    await bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data in ("broadcast:confirm", "broadcast:cancel"))
async def admin_cb_broadcast_confirm(call: types.CallbackQuery):

    state, data = await StateManager.get_state_and_data(call.from_user.id)
    await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

    if call.data == "broadcast:cancel" or str(state) != str(AdminStates.CONFIRM_BROADCAST):
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


# ── Admin text router (called from unified text_router.py) ────────────────────

async def handle_admin_text(message: types.Message, state: str, data: dict) -> bool:
    """
    Dispatch admin text input based on current StateManager state.
    Returns True if the state was handled, False if unrecognized.
    Called from bot_app/handlers/text_router.py unified catch-all.
    """
    tid = message.from_user.id
    text = message.text.strip()

    if str(state) == str(AdminStates.ADD_MANAGER_TELEGRAM_ID):
        await _handle_add_user(message, text, tid, UserRole.SALES_MANAGER,
                               AdminStates.ADD_MANAGER_NAME)
        return True

    if str(state) == str(AdminStates.ADD_MANAGER_NAME):
        await _finalize_add_user(message, text, tid, UserRole.SALES_MANAGER, "sotuvchi")
        return True

    if str(state) == str(AdminStates.ADD_AGRONOMIST_TELEGRAM_ID):
        await _handle_add_user(message, text, tid, UserRole.AGRONOMIST,
                               AdminStates.ADD_AGRONOMIST_NAME)
        return True

    if str(state) == str(AdminStates.ADD_AGRONOMIST_NAME):
        await _finalize_add_user(message, text, tid, UserRole.AGRONOMIST, "agronom")
        return True

    if str(state) == str(AdminStates.SEND_MESSAGE_SELECT_USER):
        if not text.lstrip('-').isdigit():
            await bot.send_message(message.chat.id, "⚠️ Telegram ID raqam bo'lishi kerak:")
            return True
        target_tid = int(text)
        try:
            target = await TelegramUser.objects.aget(telegram_id=target_tid)
        except TelegramUser.DoesNotExist:
            await bot.send_message(message.chat.id, f"❌ ID {target_tid} ro'yxatda yo'q.")
            return True
        await StateManager.set_state(tid, AdminStates.SEND_MESSAGE_TEXT,
                                     data={'target_id': target_tid})
        await bot.send_message(
            message.chat.id,
            f"✅ Qabul qiluvchi: <b>{target.full_name}</b>\n\nXabar matnini yozing:"
        )
        return True

    if str(state) == str(AdminStates.SEND_MESSAGE_TEXT):
        target_id = data.get('target_id')
        await StateManager.clear(tid)
        sent = await notify_user(bot, target_id, f"📩 <b>Admin xabari:</b>\n\n{text}")
        reply = "✅ Xabar yuborildi!" if sent else "❌ Xabar yuborib bo'lmadi."
        await bot.send_message(message.chat.id, reply, reply_markup=admin_main_menu())
        return True

    if str(state) == str(AdminStates.BROADCAST_TEXT):
        await StateManager.set_state(tid, AdminStates.CONFIRM_BROADCAST,
                                     data={'broadcast_text': text})
        await bot.send_message(
            message.chat.id,
            f"📢 <b>Xabar:</b>\n\n{text}\n\n"
            f"<i>Bu xabar BARCHA foydalanuvchilarga yuboriladi. Tasdiqlaysizmi?</i>",
            reply_markup=confirm_broadcast_keyboard(),
        )
        return True

    return False


async def _handle_add_user(message, text: str, admin_tid: int, role: str, next_state) -> None:
    if not text.lstrip('-').isdigit():
        await bot.send_message(message.chat.id, "⚠️ Telegram ID raqam bo'lishi kerak:")
        return
    target_tid = int(text)
    try:
        existing = await TelegramUser.objects.aget(telegram_id=target_tid)
        if existing.role == role and existing.is_active:
            await bot.send_message(
                message.chat.id,
                f"⚠️ Bu foydalanuvchi allaqachon {existing.get_role_display()} sifatida ro'yxatda."
            )
            await StateManager.clear(admin_tid)
            return
    except TelegramUser.DoesNotExist:
        pass

    await StateManager.update_data(admin_tid, new_user_telegram_id=target_tid)
    await StateManager.set_state(admin_tid, next_state,
                                 data=(await StateManager.get_data(admin_tid)))
    await bot.send_message(message.chat.id, "✅ ID qabul qilindi.\n\nTo'liq ismini kiriting:")


async def _finalize_add_user(message, name: str, admin_tid: int, role: str,
                              role_label: str) -> None:
    data = await StateManager.get_data(admin_tid)
    target_tid = data.get('new_user_telegram_id')
    if not target_tid:
        await StateManager.clear(admin_tid)
        await bot.send_message(message.chat.id, "❌ Xatolik. Qayta boshlang.",
                               reply_markup=admin_main_menu())
        return

    _, created = await TelegramUser.objects.aupdate_or_create(
        telegram_id=target_tid,
        defaults={'full_name': name, 'role': role, 'is_active': True},
    )
    await StateManager.clear(admin_tid)

    action = "qo'shildi" if created else "yangilandi"
    await bot.send_message(
        message.chat.id,
        f"✅ {role_label.capitalize()} {action}:\n"
        f"Ism: {name}\nTelegram ID: {target_tid}",
        reply_markup=admin_main_menu(),
    )

    role_greet = {"sales_manager": "Sotuvchi", "agronomist": "Agronom"}.get(role, role_label)
    await notify_user(
        bot, target_tid,
        f"🎉 Tabriklaymiz, {name}!\n\n"
        f"Siz Oscar Agro tizimiga <b>{role_greet}</b> sifatida qo'shildingiz.\n"
        f"Boshlash uchun /start bosing."
    )
