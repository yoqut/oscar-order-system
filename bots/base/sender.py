"""
Enhanced Sender — wraps bot + message/callback with language support.

Usage inside a handler:
    async def my_handler(sender: Sender, state: StateContext):
        await sender.text("Xabar matni")
        await sender.send('welcome_new', name="Ali")   # i18n key
        await sender.edit('select_lang')
        lang = sender.lang                             # user's language code
"""
from __future__ import annotations

from typing import TypeAlias

from telebot.async_telebot import AsyncTeleBot
from telebot.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from core.i18n import t

MessageLike: TypeAlias = Message | CallbackQuery
ReplyMarkup: TypeAlias = InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | None


class Sender:
    __slots__ = ('bot', 'msg', 'lang')

    def __init__(self, bot: AsyncTeleBot, msg: MessageLike, lang: str = 'uz') -> None:
        self.bot = bot
        self.msg = msg
        self.lang = lang

    # ── IDs ──────────────────────────────────────────────────────────────────

    @property
    def chat_id(self) -> int:
        if isinstance(self.msg, Message):
            return self.msg.chat.id
        return self.msg.message.chat.id

    @property
    def message_id(self) -> int:
        if isinstance(self.msg, Message):
            return self.msg.message_id
        return self.msg.message.message_id

    @property
    def user_id(self) -> int:
        return self.msg.from_user.id

    # ── Translation ───────────────────────────────────────────────────────────

    def tr(self, key: str, **kwargs) -> str:
        """Translate key using user's language."""
        return t(key, self.lang, **kwargs)

    # ── Raw text send ─────────────────────────────────────────────────────────

    async def text(self, text: str, markup: ReplyMarkup = None, parse_mode: str = 'HTML', **kwargs) -> Message:
        """Send raw text message."""
        content = text.format(**kwargs) if kwargs else text
        return await self.bot.send_message(
            self.chat_id,
            text=content,
            reply_markup=markup,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )

    # ── i18n send ─────────────────────────────────────────────────────────────

    async def send(self, key: str, markup: ReplyMarkup = None, parse_mode: str = 'HTML', **kwargs) -> Message:
        """Translate key and send as message."""
        return await self.text(self.tr(key, **kwargs), markup=markup, parse_mode=parse_mode)

    # ── Edit ──────────────────────────────────────────────────────────────────

    async def edit_text(self, text: str, markup: ReplyMarkup = None, parse_mode: str = 'HTML', **kwargs) -> Message | None:
        """Edit current message text (and optionally markup)."""
        content = text.format(**kwargs) if kwargs else text
        try:
            return await self.bot.edit_message_text(
                text=content,
                chat_id=self.chat_id,
                message_id=self.message_id,
                parse_mode=parse_mode,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
        except Exception as e:
            if 'message is not modified' in str(e):
                return None
            if markup:
                try:
                    return await self.bot.edit_message_reply_markup(
                        chat_id=self.chat_id,
                        message_id=self.message_id,
                        reply_markup=markup,
                    )
                except Exception:
                    pass
            raise

    async def edit(self, key: str, markup: ReplyMarkup = None, parse_mode: str = 'HTML', **kwargs) -> Message | None:
        """Translate key and edit current message."""
        return await self.edit_text(self.tr(key, **kwargs), markup=markup, parse_mode=parse_mode)

    async def edit_markup(self, markup: ReplyMarkup = None) -> None:
        """Edit only the reply markup of the current message."""
        try:
            await self.bot.edit_message_reply_markup(
                chat_id=self.chat_id,
                message_id=self.message_id,
                reply_markup=markup,
            )
        except Exception:
            pass

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete(self) -> None:
        try:
            await self.bot.delete_message(self.chat_id, self.message_id)
        except Exception:
            pass

    # ── Answer callback ───────────────────────────────────────────────────────

    async def answer(self, text: str = '', show_alert: bool = False) -> None:
        if isinstance(self.msg, CallbackQuery):
            try:
                await self.bot.answer_callback_query(
                    self.msg.id,
                    text=text,
                    show_alert=show_alert,
                )
            except Exception:
                pass
