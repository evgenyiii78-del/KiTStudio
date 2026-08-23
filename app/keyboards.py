from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.agents import AGENTS

BTN_CHAT = "💬 AI-чат"
BTN_IMAGE = "🎨 Создать картинку"
BTN_VISION = "🔍 Анализ фото"
BTN_AGENT = "🤖 Выбрать AI-агента"
BTN_CLEAR = "🧹 Очистить историю"
BTN_HELP = "ℹ️ Помощь"
BTN_CANCEL = "❌ Отмена"

MENU_BUTTONS = {BTN_CHAT, BTN_IMAGE, BTN_VISION, BTN_AGENT, BTN_CLEAR, BTN_HELP, BTN_CANCEL}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CHAT), KeyboardButton(text=BTN_IMAGE)],
            [KeyboardButton(text=BTN_VISION), KeyboardButton(text=BTN_AGENT)],
            [KeyboardButton(text=BTN_CLEAR), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Напишите запрос…",
    )


def agent_keyboard(current_key: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for key, agent in AGENTS.items():
        marker = "✅ " if key == current_key else ""
        rows.append([
            InlineKeyboardButton(text=f"{marker}{agent.title}", callback_data=f"agent:{key}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
