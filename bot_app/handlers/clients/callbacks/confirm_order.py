from ....states.client_states import ClientConfirmStates
from ....core.loader import bot


@bot.callback_query_handler(func=lambda call: call.data == "confirm_order", is_client=True)
async def client_confirm_order_callback(call, state):
    await state.set(ClientConfirmStates.confirm)
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Buyurtma raqamini yuboring: ",
        reply_markup=None
    )