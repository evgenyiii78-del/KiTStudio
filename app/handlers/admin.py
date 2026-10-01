from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.config import Settings
from app.database import Database
from app.keyboards import main_menu

router = Router(name="admin")
BTN_ADD="➕ Добавить пользователя"
BTN_DEL="➖ Удалить пользователя"
BTN_LIST="👥 Пользователи"
BTN_BACK="⬅️ В меню"

class AdminFlow(StatesGroup):
    add_user=State()
    del_user=State()

def admin_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_ADD),KeyboardButton(text=BTN_DEL)],[KeyboardButton(text=BTN_LIST)],[KeyboardButton(text=BTN_BACK)]],resize_keyboard=True)

def _is_admin(message:Message,settings:Settings)->bool:
    return bool(message.from_user and message.from_user.id==settings.admin_id)

@router.message(Command("admin"))
async def admin(message:Message,state:FSMContext,settings:Settings)->None:
    if not _is_admin(message,settings):
        await message.answer("⛔ Нет доступа."); return
    await state.clear(); await message.answer("🔐 <b>Администратор</b>\n\nУправление доступом к KiTstudio AI.",reply_markup=admin_menu())

@router.message(F.text==BTN_ADD)
async def add_begin(message:Message,state:FSMContext,settings:Settings)->None:
    if not _is_admin(message,settings): return
    await state.set_state(AdminFlow.add_user); await message.answer("Пришлите <b>Telegram ID</b> пользователя.")

@router.message(AdminFlow.add_user,F.text)
async def add_finish(message:Message,state:FSMContext,settings:Settings,db:Database)->None:
    if not _is_admin(message,settings): return
    try: uid=int((message.text or "").strip())
    except ValueError: await message.answer("❌ Нужен числовой Telegram ID."); return
    await db.grant_access(uid,settings.admin_id); await state.clear(); await message.answer(f"✅ Пользователь <code>{uid}</code> добавлен.",reply_markup=admin_menu())

@router.message(F.text==BTN_DEL)
async def del_begin(message:Message,state:FSMContext,settings:Settings)->None:
    if not _is_admin(message,settings): return
    await state.set_state(AdminFlow.del_user); await message.answer("Пришлите <b>Telegram ID</b> пользователя, которого удалить.")

@router.message(AdminFlow.del_user,F.text)
async def del_finish(message:Message,state:FSMContext,settings:Settings,db:Database)->None:
    if not _is_admin(message,settings): return
    try: uid=int((message.text or "").strip())
    except ValueError: await message.answer("❌ Нужен числовой Telegram ID."); return
    if uid==settings.admin_id: await message.answer("❌ Администратора удалить нельзя."); return
    await db.revoke_access(uid); await state.clear(); await message.answer(f"✅ Доступ пользователя <code>{uid}</code> удалён.",reply_markup=admin_menu())

@router.message(F.text==BTN_LIST)
async def users(message:Message,settings:Settings,db:Database)->None:
    if not _is_admin(message,settings): return
    ids=await db.list_access_users(); lines=[f"👑 <code>{settings.admin_id}</code> — администратор"]+[f"• <code>{x}</code>" for x in ids if x!=settings.admin_id]
    await message.answer("<b>Пользователи с доступом:</b>\n\n"+"\n".join(lines),reply_markup=admin_menu())

@router.message(F.text==BTN_BACK)
async def back(message:Message,state:FSMContext,settings:Settings)->None:
    if not _is_admin(message,settings): return
    await state.clear(); await message.answer("Главное меню.",reply_markup=main_menu())
