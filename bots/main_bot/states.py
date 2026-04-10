from telebot.states import State, StatesGroup


class SalesStates(StatesGroup):
    # Creating order — new flow: name → phone1 → phone2 → trees → problem → address → date → slot → agronomist → confirm
    ENTER_CLIENT_NAME = State()
    ENTER_PHONE1 = State()
    ENTER_PHONE2 = State()
    ENTER_TREE_COUNT = State()
    ENTER_PROBLEM = State()
    ENTER_ADDRESS = State()
    SELECT_DATE = State()
    SELECT_TIME_SLOT = State()
    SELECT_AGRONOMIST = State()
    CONFIRM_ORDER = State()
    # Accepting a client-created order
    ACCEPT_CLIENT_ORDER_SELECT_AGRO = State()
    ACCEPT_CLIENT_ORDER_SELECT_SLOT = State()


class AgronomistStates(StatesGroup):
    ENTER_CANCEL_REASON = State()
    ENTER_TREATMENT_COUNT = State()
    ENTER_ROOT_TREATMENT = State()
    ENTER_FINAL_PRICE = State()
    SELECT_PAYMENT_TYPE = State()
    SELECT_RETREATMENT = State()
    ENTER_RETREATMENT_DATE = State()
    UPLOAD_PROOF = State()


class AdminStates(StatesGroup):
    ADD_MANAGER_ID = State()
    ADD_MANAGER_NAME = State()
    ADD_AGRONOMIST_ID = State()
    ADD_AGRONOMIST_NAME = State()
    SEND_MESSAGE_SELECT_USER = State()
    SEND_MESSAGE_TEXT = State()
    BROADCAST_TEXT = State()
    CONFIRM_BROADCAST = State()
    CANCEL_ORDER_REASON = State()
