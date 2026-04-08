"""
CallbackData factories for all structured inline keyboard callbacks.
One shared AdvancedCustomFilter (key='config') handles them all.
"""
from telebot.callback_data import CallbackData, CallbackDataFilter
from telebot.asyncio_filters import AdvancedCustomFilter

# ── Sales ─────────────────────────────────────────────────────────────────────
agro_select_factory = CallbackData('agro_id', prefix='agro_select')
slot_factory = CallbackData('slot', prefix='slot')
order_confirm_factory = CallbackData('answer', prefix='order_confirm')

# ── Agronomist ────────────────────────────────────────────────────────────────
agro_view_factory = CallbackData('order_id', prefix='agro_view')
agro_cancel_factory = CallbackData('order_id', prefix='agro_cancel')
agro_complete_factory = CallbackData('order_id', prefix='agro_cmplt')
agro_page_factory = CallbackData('page', prefix='agro_page')
root_factory = CallbackData('value', prefix='root')
payment_factory = CallbackData('ptype', prefix='payment')
retreatment_factory = CallbackData('value', prefix='retreatment')

# ── Client ────────────────────────────────────────────────────────────────────
client_accept_factory = CallbackData('order_id', prefix='cli_accept')
client_cancel_factory = CallbackData('order_id', prefix='cli_cancel')
client_confirm_factory = CallbackData('order_id', prefix='cli_confirm')
client_reject_factory = CallbackData('order_id', prefix='cli_reject')
rate_factory = CallbackData('order_id', 'rating', prefix='rate')

# ── Admin ─────────────────────────────────────────────────────────────────────
admin_remove_factory = CallbackData('user_pk', prefix='adm_remove')
admin_approve_factory = CallbackData('order_id', prefix='adm_approve')
admin_cancel_order_factory = CallbackData('order_id', prefix='adm_cancel')

# ── Back ──────────────────────────────────────────────────────────────────────
back_factory = CallbackData('to', prefix='back')

class CustomCallbackDataFilter(AdvancedCustomFilter):
    """Single filter that handles all CallbackData factories via config= kwarg."""
    key = 'config'

    async def check(self, call, config: CallbackDataFilter):
        return config.check(query=call)
