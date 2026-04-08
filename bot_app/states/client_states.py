from telebot.states import State, StatesGroup


class ClientConfirmStates(StatesGroup):
    confirm: State = State()