"""
Shared callback data factories used across both bots.
"""
from telebot.callback_data import CallbackData

# ── Client bot notifications (sent from main bot, handled by client bot) ──────
client_accept_factory = CallbackData("order_id", prefix="cli_acc")
client_reject_factory = CallbackData("order_id", prefix="cli_rej")
client_confirm_factory = CallbackData("order_id", prefix="cli_cfm")
client_reject_service_factory = CallbackData("order_id", prefix="cli_rjs")
rate_factory = CallbackData("order_id", "rating", prefix="rate")
faq_factory = CallbackData("item_id", prefix="faq")

# ── Main bot — Sales flow ─────────────────────────────────────────────────────
agro_select_factory = CallbackData("agro_id", prefix="agro_sel")
slot_factory = CallbackData("slot", prefix="slot")
order_confirm_factory = CallbackData("answer", prefix="order_cfm")

# ── Main bot — Sales accepting client orders ─────────────────────────────────
sales_accept_client_order_factory = CallbackData("order_id", prefix="s_acc_ord")
sales_assign_agro_factory = CallbackData("order_id", "agro_id", prefix="s_agro")
sales_assign_slot_factory = CallbackData("order_id", "slot", prefix="s_slot")

# ── Main bot — Agronomist flow ────────────────────────────────────────────────
agro_view_factory = CallbackData("order_id", prefix="agro_view")
agro_cancel_factory = CallbackData("order_id", prefix="agro_cancel")
agro_complete_factory = CallbackData("order_id", prefix="agro_cmplt")
agro_page_factory = CallbackData("page", prefix="agro_page")
root_factory = CallbackData("value", prefix="root")
payment_factory = CallbackData("ptype", prefix="payment")
retreatment_factory = CallbackData("value", prefix="retreatment")

# ── Main bot — Admin flow ─────────────────────────────────────────────────────
admin_remove_factory = CallbackData("user_pk", prefix="adm_rm")
admin_approve_factory = CallbackData("order_id", prefix="adm_app")
admin_cancel_order_factory = CallbackData("order_id", prefix="adm_can")
admin_view_order_factory = CallbackData("order_id", prefix="adm_view")
