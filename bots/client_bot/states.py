from telebot.states import State, StatesGroup


class RegistrationStates(StatesGroup):
    SELECT_LANGUAGE = State()
    ENTER_NAME = State()
    ENTER_PHONE = State()


class OrderStates(StatesGroup):
    ENTER_PROBLEM = State()
    ENTER_ADDRESS = State()
    ENTER_TREE_COUNT = State()
    CONFIRM_ORDER = State()
    ENTER_CANCEL_REASON = State()
    ENTER_REJECT_REASON = State()


class ProfileStates(StatesGroup):
    EDIT_NAME = State()
    EDIT_PHONE = State()


class RatingStates(StatesGroup):
    ENTER_COMMENT = State()


class FAQStates(StatesGroup):
    VIEW_ITEM = State()
