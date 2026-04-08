from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Sequence

from telebot.asyncio_filters import AdvancedCustomFilter
from telebot.callback_data import CallbackData, CallbackDataFilter
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


# ─── core ────────────────────────────────────────────────────────────────────

async def _r(v):
    return await v if inspect.isawaitable(v) else v


@dataclass(slots=True)
class _B:
    text: Any
    p: dict[str, Any] = field(default_factory=dict)


# ─── builder ─────────────────────────────────────────────────────────────────

class KeyboardBuilder:
    __slots__ = ("_mode", "_rw", "_opts", "_flat", "_rows")

    def __init__(self, mode: str = "inline", *, row_width: int = 3, **opts):
        self._mode = mode
        self._rw   = row_width
        self._opts = opts
        self._flat: list[_B] = []
        self._rows: list[list[_B]] = []

    @classmethod
    def inline(cls, **kw) -> "kb":  return cls("inline", **kw)

    @classmethod
    def reply(cls, **kw) -> "kb":   return cls("reply", **kw)

    # ── button primitives ────────────────────────────────────────────────────

    def button(self, text: Any, **p) -> "kb":
        self._flat.append(_B(text, p)); return self

    def callback(self, text: Any, data: str, **kw) -> "kb":
        return self.button(text, callback_data=data, **kw)

    def url(self, text: Any, url: str) -> "kb":
        return self.button(text, url=url)

    def web_app(self, text: Any, web_app: Any) -> "kb":
        return self.button(text, web_app=web_app)

    def pay(self, text: Any) -> "kb":
        return self.button(text, pay=True)

    def buttons(self, items: Sequence[tuple[Any, str]], **kw) -> "kb":
        for text, data in items:
            self.callback(text, data, **kw)
        return self

    # ── layout ───────────────────────────────────────────────────────────────

    def layout(self, structure: Sequence[int]) -> "kb":
        pos = 0
        for n in structure:
            self._rows.append(self._flat[pos: pos + n]); pos += n
        self._flat = self._flat[pos:]
        return self

    def row(self) -> "kb":
        self._rows.append(list(self._flat)); self._flat = []
        return self

    # ── build ────────────────────────────────────────────────────────────────

    async def build(self, layout: Sequence[int] | None = None, row_width: int | None = None):
        if layout:
            self.layout(layout)

        rw = row_width or self._rw
        if self._flat:
            self._rows += [self._flat[i: i + rw] for i in range(0, len(self._flat), rw)]

        markup = self._markup()
        is_inline = self._mode == "inline"

        for ri, row in enumerate(self._rows):
            btns = []
            for ci, b in enumerate(row):
                text = await _r(b.text)
                p = b.p
                if p.get("pay") or p.get("callback_game"):
                    if ri or ci:
                        raise ValueError("pay/callback_game must be first button")
                btns.append(
                    InlineKeyboardButton(text, **p) if is_inline else KeyboardButton(text, **p)
                )
            markup.row(*btns)

        return markup

    def _markup(self):
        if self._mode == "inline":
            return InlineKeyboardMarkup(row_width=self._rw)
        return ReplyKeyboardMarkup(
            row_width=self._rw,
            resize_keyboard=self._opts.get("resize_keyboard", True),
            one_time_keyboard=self._opts.get("one_time_keyboard", False),
            selective=self._opts.get("selective", False),
            is_persistent=self._opts.get("is_persistent"),
        )




# ─── filter ───────────────────────────────────────────────────────────────────

