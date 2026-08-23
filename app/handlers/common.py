from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database import Database
from app.keyboards import BTN_CANCEL, BTN_HELP, main_menu

router = Router(name="common")

WELCOME = (
    "<b>КиТstudio AI</b>\n\n"
    "🎨 Генератор изображений на <b>gpt-image-2</b>.\n\n"
    "Просто напишите, какую картинку хотите получить, "
    "или нажмите «🎨 Создать картинку»."
)

HELP = (
    "<b>Как пользоваться</b>\n\n"
    "1. Напишите описание изображения обычным сообщением.\n"
    "2. Укажите объект, стиль, композицию, фон, цвета и нужный текст.\n"
    "3. Дождитесь готовой картинки.\n\n"
    "<b>Пример:</b> минималистичный торт на белом фоне, вид спереди, "
    "пастельные оттенки, надпись «С днём рождения»."
)


@router.message(CommandStart())
async def start(message: Message, db: Database, state: FSMContext) -> None:
    await state.clear()
    if message.from_user:
        await db.ensure_user(message.from_user.id)
    await message.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def help_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(HELP, reply_markup=main_menu())


@router.message(F.text == BTN_CANCEL)
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено. Просто напишите новый запрос для картинки.", reply_markup=main_menu())
