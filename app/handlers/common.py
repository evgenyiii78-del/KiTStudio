from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.agents import AGENTS, get_agent
from app.database import Database
from app.keyboards import BTN_AGENT, BTN_CANCEL, BTN_CLEAR, BTN_HELP, agent_keyboard, main_menu

router = Router(name="common")


WELCOME = (
    "<b>CakeHub AI Bot 3.4</b>\n\n"
    "AI-чат, генерация изображений и анализ фотографий через AITunnel.\n"
    "Выберите действие на нижней панели или просто напишите вопрос."
)

HELP = (
    "<b>Что умеет бот</b>\n\n"
    "💬 <b>AI-чат</b> — задайте любой вопрос.\n"
    "🎨 <b>Создать картинку</b> — отправьте описание изображения.\n"
    "🔍 <b>Анализ фото</b> — отправьте фотографию и вопрос в подписи.\n"
    "🤖 <b>Выбрать AI-агента</b> — меняет специализацию ответов.\n"
    "🧹 <b>Очистить историю</b> — удаляет вашу историю текущего чата.\n\n"
    "<b>В группе</b>: вызовите бота по @username или слову «КейкХаб». "
    "Команда /bot_on включает ответы на все сообщения группы, /bot_off выключает."
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


@router.message(F.text == "💬 AI-чат")
async def chat_hint(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Напишите вопрос — отвечу с учётом выбранного AI-агента.")


@router.message(F.text == BTN_CLEAR)
async def clear_history(message: Message, db: Database, state: FSMContext) -> None:
    await state.clear()
    if not message.from_user:
        return
    await db.clear_history(message.chat.id, message.from_user.id)
    await message.answer("История этого чата очищена.", reply_markup=main_menu())


@router.message(F.text == BTN_AGENT)
async def choose_agent(message: Message, db: Database, state: FSMContext) -> None:
    await state.clear()
    if not message.from_user:
        return
    current = await db.get_agent_key(message.from_user.id)
    agent = get_agent(current)
    await message.answer(
        f"Сейчас выбран: <b>{agent.title}</b>\n{agent.description}\n\nВыберите другого агента:",
        reply_markup=agent_keyboard(current),
    )


@router.callback_query(F.data.startswith("agent:"))
async def set_agent(callback: CallbackQuery, db: Database) -> None:
    if not callback.from_user or not callback.data:
        return
    key = callback.data.split(":", 1)[1]
    if key not in AGENTS:
        await callback.answer("Неизвестный агент", show_alert=True)
        return
    await db.set_agent_key(callback.from_user.id, key)
    agent = AGENTS[key]
    if callback.message:
        await callback.message.edit_text(
            f"Выбран агент: <b>{agent.title}</b>\n{agent.description}",
            reply_markup=agent_keyboard(key),
        )
    await callback.answer("Агент выбран")


async def _is_admin(message: Message, bot: Bot) -> bool:
    if not message.from_user:
        return False
    if message.chat.type == ChatType.PRIVATE:
        return True
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


@router.message(Command("bot_on"))
async def bot_on(message: Message, db: Database, bot: Bot) -> None:
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("В личном чате бот уже активен.")
        return
    if not await _is_admin(message, bot):
        await message.answer("Команду /bot_on может использовать администратор группы.")
        return
    await db.set_group_enabled(message.chat.id, True)
    await message.answer("CakeHub включён для всех сообщений этой группы. /bot_off — выключить.")


@router.message(Command("bot_off"))
async def bot_off(message: Message, db: Database, bot: Bot) -> None:
    if message.chat.type == ChatType.PRIVATE:
        return
    if not await _is_admin(message, bot):
        await message.answer("Команду /bot_off может использовать администратор группы.")
        return
    await db.set_group_enabled(message.chat.id, False)
    await message.answer("Автоответы выключены. Бота всё ещё можно вызвать по @username или слову «КейкХаб».")


@router.message(F.text == BTN_CANCEL)
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu())
