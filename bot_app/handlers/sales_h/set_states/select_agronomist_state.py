from telebot import types
from telebot.states.asyncio import StateContext

from apps.accounts.models import TelegramUser, UserRole
from apps.orders.models import Order
from ....core.callback_factories import agro_select_factory
from ....keyboards.sales_kb import time_slot_keyboard
from ....core.loader import bot
from ....core.use_states import SalesStates


@bot.callback_query_handler(func=None, config=agro_select_factory.filter(),
                            state=SalesStates.SELECT_AGRONOMIST)
async def sales_cb_select_agronomist(call: types.CallbackQuery, state: StateContext):
    cb = agro_select_factory.parse(call.data)
    agro_id = int(cb['agro_id'])

    try:
        agro = await TelegramUser.objects.aget(pk=agro_id, role=UserRole.AGRONOMIST)
    except TelegramUser.DoesNotExist:
        await bot.answer_callback_query(call.id, "❌ Agronom topilmadi")
        return

    orders = Order.objects.filter(
        agronomist=agro
    ).only("id", "time_slot")

    orders = [o async for o in orders]

    await state.add_data(agronomist_id=agro_id, agronomist_name=agro.full_name)
    await state.set(SalesStates.SELECT_TIME_SLOT)
    await bot.edit_message_text(
        f"✅ Agronom: <b>{agro.full_name}</b>\n\n⏰ Vaqt oralig'ini tanlang:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=time_slot_keyboard(orders),
    )
    await bot.answer_callback_query(call.id)