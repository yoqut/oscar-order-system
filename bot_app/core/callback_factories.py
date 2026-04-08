from telebot.callback_data import CallbackData


# ─── factory helper ──────────────────────────────────────────────────────────

def _f(prefix: str, *fields: str) -> CallbackData:
    return CallbackData(*fields, prefix=prefix)


# ─── callback factories ───────────────────────────────────────────────────────

# sales
agro_select_factory   = _f("agro_sel",   "agro_id")
slot_factory          = _f("slot",        "slot")
order_confirm_factory = _f("order_cfm",   "answer")

# agronomist
agro_view_factory     = _f("agro_view",   "order_id")
agro_cancel_factory   = _f("agro_cancel", "order_id")
agro_complete_factory = _f("agro_cmplt",  "order_id")
agro_page_factory     = _f("agro_page",   "page")
root_factory          = _f("root",        "value")
payment_factory       = _f("payment",     "ptype")
retreatment_factory   = _f("retreatment", "value")

# client
client_accept_factory  = _f("cli_accept",  "order_id")
client_cancel_factory  = _f("cli_cancel",  "order_id")
client_confirm_factory = _f("cli_confirm", "order_id")
client_reject_factory  = _f("cli_reject",  "order_id")
rate_factory           = _f("rate",        "order_id", "rating")

# admin
admin_remove_factory       = _f("adm_remove",  "user_pk")
admin_approve_factory      = _f("adm_approve", "order_id")
admin_cancel_order_factory = _f("adm_cancel",  "order_id")

# nav
back_factory = _f("back", "to")