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

MessageLike: TypeAlias = Message | CallbackQuery
ReplyMarkup: TypeAlias = InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | None


class Sender:
    __slots__ = ("bot", "msg")

    def __init__(
            self,
            bot: AsyncTeleBot,
            msg: MessageLike,
    ) -> None:
        self.bot = bot
        self.msg = msg

    @property
    def chat_id(self) -> int:
        try:
            if isinstance(self.msg, Message):
                return self.msg.chat.id
            else:
                return self.msg.message.chat.id
        except Exception as e:
            print(e)
            return 2

    @property
    def message_id(self):
        if isinstance(self.msg, Message):
            return self.msg.message_id
        else:
            return self.msg.message.message_id

    async def text(self, slug: str, markup=None, parse_mode=None, **kwargs):


        text = slug.format(**kwargs) if kwargs else slug

        return await self.bot.send_message(
            self.chat_id,
            text=text,
            reply_markup=markup,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )

    async def edit_all(self, slug: str, markup=None, parse_mode=None, **kwargs):
        text = slug.format(**kwargs) if kwargs else slug

        try:
            # 🔥 HAMMASINI BITTA REQUESTDA QILAMIZ
            return await self.bot.edit_message_text(
                text=text,
                chat_id=self.chat_id,
                message_id=self.message_id,
                parse_mode=parse_mode,
                reply_markup=markup,
                disable_web_page_preview=True,
            )

        except Exception as e:
            # ⚠️ eng ko‘p uchraydigan errorni ignore qilamiz
            if "message is not modified" in str(e):
                return None

            # 🔁 fallback: faqat markupni yangilash
            try:
                if markup:
                    return await self.bot.edit_message_reply_markup(
                        chat_id=self.chat_id,
                        message_id=self.message_id,
                        reply_markup=markup,
                    )
            except Exception:
                pass

            raise e

    async def delete(self):
        return await self.bot.delete_message(self.chat_id, self.message_id)
