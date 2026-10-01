from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_IMAGE = "🎨 Создать картинку"
BTN_VIDEO = "🎬 Видео AI"
BTN_HELP = "ℹ️ Помощь"
BTN_CANCEL = "❌ Отмена"

MENU_BUTTONS = {BTN_IMAGE, BTN_VIDEO, BTN_HELP, BTN_CANCEL}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_IMAGE), KeyboardButton(text=BTN_VIDEO)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Опишите картинку или выберите Видео AI…",
    )
