"""
FSM state constants.
Naming convention: <role>:<step>
"""
from telebot.states import State, StatesGroup

class SalesStates:
    SELECT_AGRONOMIST = 'sales:select_agronomist'
    SELECT_TIME_SLOT = 'sales:select_time_slot'
    ENTER_CLIENT_NAME = 'sales:enter_client_name'
    ENTER_PHONE1 = 'sales:enter_phone1'
    ENTER_PHONE2 = 'sales:enter_phone2'
    ENTER_TREE_COUNT = 'sales:enter_tree_count'
    ENTER_PROBLEM = 'sales:enter_problem'
    ENTER_ADDRESS = 'sales:enter_address'
    CONFIRM_ORDER = 'sales:confirm_order'


class AgronomistStates:
    ENTER_CANCEL_REASON = 'agro:enter_cancel_reason'
    ENTER_TREATMENT_COUNT = 'agro:enter_treatment_count'
    ENTER_ROOT_TREATMENT = 'agro:enter_root_treatment'
    ENTER_FINAL_PRICE = 'agro:enter_final_price'
    SELECT_PAYMENT_TYPE = 'agro:select_payment_type'
    SELECT_RETREATMENT = 'agro:select_retreatment'
    ENTER_RETREATMENT_DATE = 'agro:enter_retreatment_date'
    UPLOAD_PROOF = 'agro:upload_proof'


class ClientStates:
    ENTER_CANCEL_REASON = 'client:enter_cancel_reason'
    ENTER_RATING = 'client:enter_rating'
    ENTER_COMMENT = 'client:enter_comment'


class AdminStates:
    ADD_MANAGER_TELEGRAM_ID = 'admin:add_manager_telegram_id'
    ADD_MANAGER_NAME = 'admin:add_manager_name'
    ADD_AGRONOMIST_TELEGRAM_ID = 'admin:add_agronomist_telegram_id'
    ADD_AGRONOMIST_NAME = 'admin:add_agronomist_name'
    SEND_MESSAGE_SELECT_USER = 'admin:send_msg_select_user'
    SEND_MESSAGE_TEXT = 'admin:send_msg_text'
    BROADCAST_TEXT = 'admin:broadcast_text'
    CONFIRM_BROADCAST = 'admin:confirm_broadcast'

class AdminAddSalesManager(StatesGroup):
    tg_id: State = State()