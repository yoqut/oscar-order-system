"""
FSM state constants using pyTelegramBotAPI native StatesGroup.
"""
from telebot.states import State, StatesGroup


class SalesStates(StatesGroup):
    SELECT_AGRONOMIST = State()
    SELECT_TIME_SLOT = State()
    ENTER_CLIENT_NAME = State()
    ENTER_PHONE1 = State()
    ENTER_PHONE2 = State()
    ENTER_TREE_COUNT = State()
    ENTER_PROBLEM = State()
    ENTER_ADDRESS = State()
    CONFIRM_ORDER = State()


class AgronomistStates(StatesGroup):
    ENTER_CANCEL_REASON = State()
    ENTER_TREATMENT_COUNT = State()
    ENTER_ROOT_TREATMENT = State()
    ENTER_FINAL_PRICE = State()
    SELECT_PAYMENT_TYPE = State()
    SELECT_RETREATMENT = State()
    ENTER_RETREATMENT_DATE = State()
    UPLOAD_PROOF = State()


class ClientStates(StatesGroup):
    ENTER_CANCEL_REASON = State()
    ENTER_RATING = State()
    ENTER_COMMENT = State()


class AdminStates(StatesGroup):
    ADD_MANAGER_TELEGRAM_ID = State()
    ADD_MANAGER_NAME = State()
    ADD_AGRONOMIST_TELEGRAM_ID = State()
    ADD_AGRONOMIST_NAME = State()
    SEND_MESSAGE_SELECT_USER = State()
    SEND_MESSAGE_TEXT = State()
    BROADCAST_TEXT = State()
    CONFIRM_BROADCAST = State()


# Kept for backward-compatibility; admin flows now use AdminStates + StateManager.
class AdminAddSalesManager(StatesGroup):
    tg_id = State()
    name = State()
