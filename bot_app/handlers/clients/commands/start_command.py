import logging
from telebot import types
from telebot.states.asyncio.context import StateContext

from ....core.loader import bot
from ....utils.helpers import get_or_create_user
from ....keyboards.inlines.client import client_mm_inl

logger = logging.getLogger(__name__)

@bot.message_handler(commands=['start'], is_client=True)
async def client_cmd_start(message: types.Message, state: StateContext):
    user = await get_or_create_user(message)
    await state.delete()
    await bot.send_message(
        message.chat.id,
        f"👋 Salom, <b>{user.full_name}</b>!\n\n"
        "Siz bu bot orqali buyurtmalaringizni kuzatishingiz mumkin.\n"
        "Buyurtma yaratish uchun sotuvchiga murojaat qiling.",
        reply_markup=client_mm_inl()
    )
