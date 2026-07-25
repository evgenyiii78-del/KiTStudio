from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton

def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text="🎨 Создать изображение",callback_data="generate"),InlineKeyboardButton(text="🖼 Галерея",callback_data="gallery")],
      [InlineKeyboardButton(text="✨ Улучшить фото",callback_data="enhance"),InlineKeyboardButton(text="🪄 Удалить фон",callback_data="remove_bg")],
      [InlineKeyboardButton(text="🔍 Анализ фото",callback_data="analyze")]
    ])
