from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_IMAGE = "🎨 Создать картинку"
BTN_HELP = "ℹ️ Помощь"
BTN_CANCEL = "❌ Отмена"

MENU_BUTTONS = {BTN_IMAGE, BTN_HELP, BTN_CANCEL}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_IMAGE)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Опишите картинку…",
    )
