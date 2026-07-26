from aiogram import F, Router
from aiogram.types import Message
from app.keyboards import main_keyboard, BTN_CHAT, BTN_IMAGE, BTN_ANALYZE, BTN_AGENT, BTN_CLEAR, BTN_HELP

router=Router()
BUTTONS={BTN_CHAT,BTN_IMAGE,BTN_ANALYZE,BTN_AGENT,BTN_CLEAR,BTN_HELP}

def invoked(text:str,username:str,names:tuple[str,...])->bool:
    low=text.lower()
    return (username and f"@{username}" in low) or any(name in low for name in names)

@router.message(F.text)
async def text_chat(message:Message,db,ai,bot_username:str):
    text=(message.text or "").strip()
    if not text or text in BUTTONS or text.startswith("/"): return
    if message.chat.type!="private":
        always=await db.group_always_on(message.chat.id)
        if not always and not invoked(text,bot_username,ai.s.bot_call_names): return
        if not always:
            await db.set_group_always_on(message.chat.id,True)
            text=text.replace(f"@{bot_username}","").strip()
    status=await message.answer("💭 Думаю…")
    try:
        uid=message.from_user.id
        history=await db.history(message.chat.id,uid,ai.s.history_limit)
        agent=await db.get_agent(message.chat.id,uid)
        answer=await ai.chat(history,text,agent)
        await db.add_message(message.chat.id,uid,"user",text)
        await db.add_message(message.chat.id,uid,"assistant",answer)
        await message.answer(answer,reply_markup=main_keyboard)
    except Exception as e:
        await message.answer(f"❌ Ошибка AI: <code>{str(e)[:700]}</code>",reply_markup=main_keyboard)
    finally:
        await status.delete()
