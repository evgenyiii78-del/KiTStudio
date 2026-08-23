from __future__ import annotations

from aiogram.types import Message

TELEGRAM_SAFE_TEXT = 3900


def split_text(text: str, limit: int = TELEGRAM_SAFE_TEXT) -> list[str]:
    text = (text or "").strip()
    if not text:
        return ["AI вернул пустой ответ."]
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    rest = text
    while len(rest) > limit:
        cut = rest.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = rest.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip()
    if rest:
        parts.append(rest)
    return parts


async def reply_long(message: Message, text: str) -> None:
    for part in split_text(text):
        await message.answer(part, parse_mode=None)
