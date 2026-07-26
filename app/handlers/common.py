from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from app.agents import AGENTS
from app.keyboards import main_keyboard, agents_keyboard, BTN_AGENT, BTN_CLEAR, BTN_HELP, BTN_CHAT

router = Router()

WELCOME = """<b>CakeHub AI Bot 3.4</b>

Я работаю только через AITunnel. Могу отвечать на вопросы, анализировать фотографии и создавать изображения.

Выберите действие на нижней панели или просто напишите сообщение."""


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(WELCOME, reply_markup=main_keyboard)


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def help_cmd(message: Message):
    text = """<b>Команды</b>
/start — показать панель
/agent — выбрать агента
/image — создать картинку
/clear — очистить историю
/bot_on и /bot_off — ответы в группе

Для анализа нажмите «🔍 Анализ фото» и отправьте фотографию."""
    await message.answer(text, reply_markup=main_keyboard)


@router.message(Command("agent"))
@router.message(F.text == BTN_AGENT)
async def agent_menu(message: Message, db):
    key = await db.get_agent(message.chat.id, message.from_user.id)
    await message.answer("Выберите AI-агента:", reply_markup=agents_keyboard(key))


@router.callback_query(F.data.startswith("agent:"))
async def agent_select(call: CallbackQuery, db):
    key = call.data.split(":", 1)[1]
    if key not in AGENTS:
        await call.answer("Неизвестный агент", show_alert=True)
        return
    await db.set_agent(call.message.chat.id, call.from_user.id, key)
    await call.message.edit_text(
        f"Выбран агент: <b>{AGENTS[key][0]}</b>",
        reply_markup=agents_keyboard(key),
    )
    await call.answer("Агент выбран")


@router.message(Command("clear"))
@router.message(F.text == BTN_CLEAR)
async def clear(message: Message, db):
    await db.clear_history(message.chat.id, message.from_user.id)
    await message.answer("История диалога очищена.", reply_markup=main_keyboard)


@router.message(F.text == BTN_CHAT)
async def chat_hint(message: Message):
    await message.answer(
        "Напишите вопрос обычным сообщением — выбранный AI-агент ответит.",
        reply_markup=main_keyboard,
    )


@router.message(Command("bot_on"))
async def bot_on(message: Message, db):
    if message.chat.type == "private":
        await message.answer("В личном чате бот и так отвечает всегда.")
        return
    await db.set_group_always_on(message.chat.id, True)
    await message.answer("Постоянные ответы в этой группе включены.")


@router.message(Command("bot_off"))
async def bot_off(message: Message, db):
    await db.set_group_always_on(message.chat.id, False)
    await message.answer("Постоянные ответы в этой группе отключены.")
