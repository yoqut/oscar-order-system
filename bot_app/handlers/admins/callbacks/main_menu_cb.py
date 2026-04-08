import logging
from telebot import types

from ....core.loader import bot
from ....decorator.sender import Sender
from ....decorator.handle import handler
from ....keyboards.admin_kb import notifications_menu_keyboard, orders_menu_keyboard, user_management_keyboard
from ....handlers.admins.utils.stats import _send_statistics

logger = logging.getLogger(__name__)

@handler(call="notification", is_admin=True)
async def admin_notifications_menu(sender: Sender):
    await sender.text(
        "📢 <b>Xabar yuborish:</b>",
        markup=notifications_menu_keyboard(),
    )

@bot.callback_query_handler(call="notification", is_admin=True)
async def admin_notifications_menu(call: types.CallbackQuery):
    await bot.answer_callback_query(call.id)
    await bot.send_message(
        call.message.chat.id,
        "📢 <b>Xabar yuborish:</b>",
        reply_markup=notifications_menu_keyboard(),
    )


@bot.callback_query_handler(call="orders", is_admin=True)
async def admin_orders_menu(call: types.CallbackQuery):
    await bot.answer_callback_query(call.id)
    await bot.send_message(
        call.message.chat.id,
        "📦 <b>Buyurtmalar:</b>",
        reply_markup=orders_menu_keyboard(),
    )

@bot.callback_query_handler(call="stats", is_admin=True)
async def admin_statistics_cb(call: types.CallbackQuery):
    await bot.answer_callback_query(call.id)
    await _send_statistics(call.message.chat.id)

@bot.callback_query_handler(call="users", is_admin=True)
async def admin_users_menu(call: types.CallbackQuery):

    await bot.edit_message_text(
        "👥 <b>Foydalanuvchilar boshqaruvi:</b>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=user_management_keyboard(),
    )