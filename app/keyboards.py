from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from app.agents import AGENTS

BTN_CHAT = "💬 AI-чат"
BTN_IMAGE = "🎨 Создать картинку"
BTN_ANALYZE = "🔍 Анализ фото"
BTN_AGENT = "🤖 Выбрать AI-агента"
BTN_CLEAR = "🧹 Очистить историю"
BTN_HELP = "ℹ️ Помощь"

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_CHAT), KeyboardButton(text=BTN_IMAGE)],
        [KeyboardButton(text=BTN_ANALYZE), KeyboardButton(text=BTN_AGENT)],
        [KeyboardButton(text=BTN_CLEAR), KeyboardButton(text=BTN_HELP)],
    ],
    resize_keyboard=True,
    input_field_placeholder="Напишите сообщение или выберите действие…",
    is_persistent=True,
)

def agents_keyboard(selected: str) -> InlineKeyboardMarkup:
    rows=[]
    for key,(title,_) in AGENTS.items():
        mark = "✅ " if key == selected else ""
        rows.append([InlineKeyboardButton(text=mark+title, callback_data=f"agent:{key}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
