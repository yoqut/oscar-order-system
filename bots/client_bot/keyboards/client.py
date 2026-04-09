from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from core.i18n import t
from core.callbacks import (
    client_accept_factory, client_reject_factory,
    client_confirm_factory, client_reject_service_factory,
    rate_factory, faq_factory,
)


# ── Language selection ────────────────────────────────────────────────────────

def language_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang:uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton("🇺🇿 Ўзбек", callback_data="lang:uz_kr"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
    )
    return kb


# ── Phone sharing ─────────────────────────────────────────────────────────────

def share_phone_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton(t('share_phone_btn', lang), request_contact=True))
    return kb


# ── Main menu ─────────────────────────────────────────────────────────────────

def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row(KeyboardButton(t('btn_orders', lang)))
    kb.row(KeyboardButton(t('btn_profile', lang)), KeyboardButton(t('btn_faq', lang)))
    kb.row(KeyboardButton(t('btn_contact', lang)), KeyboardButton(t('btn_prices', lang)))
    return kb


# ── Orders menu ───────────────────────────────────────────────────────────────

def orders_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(
        KeyboardButton(t('btn_create_order', lang)),
        KeyboardButton(t('btn_active_orders', lang)),
        KeyboardButton(t('btn_order_history', lang)),
        KeyboardButton(t('btn_back', lang)),
    )
    return kb


# ── Cancel keyboard ───────────────────────────────────────────────────────────

def cancel_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(t('btn_cancel', lang)))
    return kb


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ── Order confirmation ────────────────────────────────────────────────────────

def confirm_order_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t('btn_confirm', lang), callback_data="order:confirm"),
        InlineKeyboardButton(t('btn_cancel', lang), callback_data="order:cancel"),
    )
    return kb


# ── Order notification (sent from main bot when sales creates order) ──────────

def order_notification_keyboard(order_id: int, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t('btn_accept_order', lang), callback_data=client_accept_factory.new(order_id=order_id)),
        InlineKeyboardButton(t('btn_reject_order', lang), callback_data=client_reject_factory.new(order_id=order_id)),
    )
    return kb


# ── Service done notification ─────────────────────────────────────────────────

def service_done_keyboard(order_id: int, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t('btn_confirm_service', lang), callback_data=client_confirm_factory.new(order_id=order_id)),
        InlineKeyboardButton(t('btn_reject_service', lang), callback_data=client_reject_service_factory.new(order_id=order_id)),
    )
    return kb


# ── Rating keyboard ───────────────────────────────────────────────────────────

def rating_keyboard(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=5)
    kb.add(*[
        InlineKeyboardButton(f"{'⭐' * i}", callback_data=rate_factory.new(order_id=order_id, rating=str(i)))
        for i in range(1, 6)
    ])
    return kb


def skip_comment_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t('btn_skip', lang), callback_data="comment:skip"))
    return kb


# ── Profile keyboard ──────────────────────────────────────────────────────────

def profile_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton(t('btn_edit_name', lang), callback_data="profile:edit_name"),
        InlineKeyboardButton(t('btn_edit_phone', lang), callback_data="profile:edit_phone"),
        InlineKeyboardButton(t('btn_change_lang', lang), callback_data="profile:change_lang"),
    )
    return kb


# ── FAQ keyboard ──────────────────────────────────────────────────────────────

def faq_keyboard(items, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for item in items:
        question = item.get_question(lang)
        kb.add(InlineKeyboardButton(
            question[:60],
            callback_data=faq_factory.new(item_id=item.pk),
        ))
    return kb


def faq_back_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t('btn_back', lang), callback_data="faq:back"))
    return kb
