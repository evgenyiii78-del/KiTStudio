from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message

from app.agents import get_agent
from app.config import Settings
from app.database import Database
from app.keyboards import MENU_BUTTONS
from app.services.ai import AIService, AIServiceError
from app.utils import reply_long

router = Router(name="chat")
logger = logging.getLogger(__name__)


def _strip_group_trigger(text: str, bot_username: str, trigger_name: str) -> str:
    result = text
    if bot_username:
        result = result.replace(f"@{bot_username}", "")
        result = result.replace(f"@{bot_username.lower()}", "")
    lower = result.lower()
    pos = lower.find(trigger_name)
    if pos >= 0:
        result = result[:pos] + result[pos + len(trigger_name):]
    return result.strip(" ,:;-\n\t")


async def _should_answer_group(
    message: Message,
    db: Database,
    bot_username: str,
    trigger_name: str,
) -> bool:
    if message.chat.type == ChatType.PRIVATE:
        return True
    if await db.is_group_enabled(message.chat.id):
        return True
    text = message.text or ""
    lower = text.lower()
    return (bool(bot_username) and f"@{bot_username.lower()}" in lower) or trigger_name in lower


@router.message(F.text & ~F.text.startswith("/"))
async def chat_message(
    message: Message,
    db: Database,
    ai: AIService,
    settings: Settings,
    bot_username: str,
) -> None:
    if not message.from_user or not message.text:
        return
    if message.text in MENU_BUTTONS:
        return
    if not await _should_answer_group(message, db, bot_username, settings.group_trigger_name):
        return

    text = message.text.strip()
    if message.chat.type != ChatType.PRIVATE:
        text = _strip_group_trigger(text, bot_username, settings.group_trigger_name)
        if not text:
            await message.answer("Да, я здесь. Напишите вопрос.")
            return

    agent_key = await db.get_agent_key(message.from_user.id)
    agent = get_agent(agent_key)

    await db.add_message(message.chat.id, message.from_user.id, "user", text)
    history = await db.get_history(
        message.chat.id,
        message.from_user.id,
        settings.history_limit,
    )

    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
        answer = await ai.chat(history, agent.system_prompt)
    except AIServiceError as exc:
        logger.warning("AI error for user %s: %s", message.from_user.id, exc)
        await message.answer(f"⚠️ {exc}", parse_mode=None)
        return
    except Exception:
        logger.exception("Unhandled chat error")
        await message.answer("⚠️ Не удалось получить ответ AI. Подробности записаны в лог.")
        return

    await db.add_message(message.chat.id, message.from_user.id, "assistant", answer)
    await reply_long(message, answer)
