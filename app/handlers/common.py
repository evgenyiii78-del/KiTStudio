from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import Settings
from app.database import Database
from app.keyboards import BTN_CANCEL, BTN_HELP, main_menu

router = Router(name="common")
WELCOME=("<b>КиТstudio AI</b>\n\n🎨 Генератор изображений на <b>gpt-image-2</b>.\n\nПросто напишите, какую картинку хотите получить, или нажмите «🎨 Создать картинку».")
HELP=("<b>Как пользоваться</b>\n\n1. Напишите описание изображения обычным сообщением.\n2. Укажите объект, стиль, композицию, фон, цвета и нужный текст.\n3. Дождитесь готовой картинки.")

@router.message(CommandStart())
async def start(message:Message,db:Database,state:FSMContext,settings:Settings)->None:
    await state.clear()
    if not message.from_user:return
    uid=message.from_user.id
    if uid!=settings.admin_id and not await db.has_access(uid):
        await message.answer(f"⛔ <b>Доступ к боту закрыт.</b>\n\nВаш Telegram ID: <code>{uid}</code>\nПередайте этот ID администратору для добавления.")
        return
    await db.ensure_user(uid)
    extra="\n\n🔐 Команда администратора: /admin" if uid==settings.admin_id else ""
    await message.answer(WELCOME+extra,reply_markup=main_menu())

@router.message(Command("help"))
@router.message(F.text==BTN_HELP)
async def help_handler(message:Message,state:FSMContext)->None:
    await state.clear(); await message.answer(HELP,reply_markup=main_menu())

@router.message(F.text==BTN_CANCEL)
async def cancel(message:Message,state:FSMContext)->None:
    await state.clear(); await message.answer("Отменено. Просто напишите новый запрос для картинки.",reply_markup=main_menu())
