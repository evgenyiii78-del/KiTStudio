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


def _is_reply_to_bot(message: Message, bot_username: str) -> bool:
    reply = message.reply_to_message
    if not reply or not reply.from_user or not reply.from_user.is_bot:
        return False
    username = (reply.from_user.username or "").lower()
    return bool(bot_username and username == bot_username.lower())


async def _should_answer_group(message: Message, db: Database, bot_username: str, trigger_name: str) -> bool:
    if message.chat.type == ChatType.PRIVATE:
        return True
    if _is_reply_to_bot(message, bot_username):
        return True
    if await db.is_group_enabled(message.chat.id):
        return True
    text = message.text or ""
    lower = text.lower()
    return (bool(bot_username) and f"@{bot_username.lower()}" in lower) or trigger_name in lower


@router.message(F.text & ~F.text.startswith("/"))
async def chat_message(message: Message, db: Database, ai: AIService, settings: Settings, bot_username: str) -> None:
    if not message.from_user or not message.text:
        return
    logger.info("TG TEXT | chat=%s type=%s user=%s @%s msg=%s reply_to=%s text=%r", message.chat.id, message.chat.type, message.from_user.id, message.from_user.username or "-", message.message_id, message.reply_to_message.message_id if message.reply_to_message else None, message.text[:500])
    if message.text in MENU_BUTTONS:
        logger.info("TG TEXT | ignored menu button")
        return
    if not await _should_answer_group(message, db, bot_username, settings.group_trigger_name):
        logger.info("TG TEXT | ignored group message: no mention/trigger/reply")
        return

    text = message.text.strip()
    if message.chat.type != ChatType.PRIVATE:
        text = _strip_group_trigger(text, bot_username, settings.group_trigger_name)
        if not text:
            await message.reply("Да, я здесь. Напишите вопрос.")
            return

    agent_key = await db.get_agent_key(message.from_user.id)
    agent = get_agent(agent_key)
    await db.add_message(message.chat.id, message.from_user.id, "user", text)
    history = await db.get_history(message.chat.id, message.from_user.id, settings.history_limit)

    try:
        logger.info("AI CHAT -> | user=%s agent=%s history=%s prompt=%r", message.from_user.id, agent_key, len(history), text[:500])
        await message.bot.send_chat_action(message.chat.id, "typing")
        answer = await ai.chat(history, agent.system_prompt)
        logger.info("AI CHAT <- | user=%s answer_chars=%s", message.from_user.id, len(answer))
    except AIServiceError as exc:
        logger.warning("AI CHAT ERROR | user=%s error=%s", message.from_user.id, exc)
        await message.reply(f"⚠️ {exc}", parse_mode=None)
        return
    except Exception:
        logger.exception("Unhandled chat error")
        await message.reply("⚠️ Не удалось получить ответ AI. Подробности записаны в лог.")
        return

    await db.add_message(message.chat.id, message.from_user.id, "assistant", answer)
    if message.chat.type == ChatType.PRIVATE:
        await reply_long(message, answer)
    else:
        # Первый фрагмент ответа в группе обязательно привязываем Reply к сообщению пользователя.
        parts = [answer[i:i + 4000] for i in range(0, len(answer), 4000)] or [answer]
        for part in parts:
            await message.reply(part)
    logger.info("TG TEXT DONE | chat=%s user=%s", message.chat.id, message.from_user.id)
