"""
Handles /start and routes users to their role-specific menus.
Also handles the /order_<id> deep-link for clients to view an order.
"""
from telebot.states.asyncio import StateContext

from bot_app.decorator import handler, Sender
from bot_app.keyboards.admin_kb import admin_main_menu
from bot_app.utils.helpers import get_or_create_user

@handler(commands=['start'], is_admin=True)
async def admin_cmd_start(sender: Sender, state: StateContext):
    user = await get_or_create_user(sender.msg)
    await state.delete()
    await sender.text(
        "👑 Xush kelibsiz, <b>{fullname}</b>!\nAdmin paneli:",
        markup=admin_main_menu(),
        fullname=user.full_name
    )