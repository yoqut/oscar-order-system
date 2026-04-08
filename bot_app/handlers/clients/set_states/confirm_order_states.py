from telebot import types
from telebot.states.asyncio import StateContext

from ....core.loader import bot
from ....states.client_states import ClientConfirmStates


@bot.message_handler(state=ClientConfirmStates.confirm)
async def confirm_order_state(msg: types.Message, state: StateContext):
    await state.delete()
    await bot.send_message(
        chat_id=msg.chat.id,
        text="Buyurtmachi aniqlandi"
    )