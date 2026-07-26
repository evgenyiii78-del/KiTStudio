from pathlib import Path
import re
import uuid
from aiogram import Router,F,Bot
from aiogram.filters import Command,CommandStart
from aiogram.types import Message,CallbackQuery,FSInputFile,ReplyKeyboardRemove
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State,StatesGroup
from app.config import settings
from app.db import database as db
from app.services.github_models import GitHubModels
from app.services.images import ImageService
from app.services.queue import Job,JobQueue

router=Router(); gh=GitHubModels(); images=ImageService(); queue=JobQueue(settings.max_queue_size,settings.workers)
class Flow(StatesGroup): waiting_prompt=State(); waiting_photo=State(); waiting_edit_prompt=State()


def _is_private(m: Message) -> bool:
    return m.chat.type == ChatType.PRIVATE

def _is_reply_to_bot(m: Message, bot_id: int) -> bool:
    return bool(m.reply_to_message and m.reply_to_message.from_user and m.reply_to_message.from_user.id == bot_id)

def _contains_call_name(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(rf"(?<!\w){re.escape(name)}(?!\w)", lowered) for name in settings.call_names)

def _strip_bot_call(text: str, username: str | None) -> str:
    cleaned = text
    if username:
        cleaned = re.sub(rf"@{re.escape(username)}\b", "", cleaned, flags=re.IGNORECASE)
    for name in settings.call_names:
        cleaned = re.sub(rf"(?<!\w){re.escape(name)}(?!\w)[,:!\-— ]*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip() or "Привет! Представься и расскажи, чем можешь помочь."

async def _should_answer_group(m: Message, bot: Bot) -> tuple[bool, str]:
    if _is_private(m):
        return True, m.text or ""
    if not m.text or not m.from_user or m.from_user.is_bot:
        return False, ""
    me = await bot.get_me()
    username = me.username or ""
    mentioned = bool(username and re.search(rf"@{re.escape(username)}\b", m.text, re.IGNORECASE))
    called_by_name = _contains_call_name(m.text)
    replied = _is_reply_to_bot(m, me.id)
    always = await db.is_chat_always_reply(m.chat.id)
    if mentioned or called_by_name:
        await db.set_chat_always_reply(m.chat.id, True)
        return True, _strip_bot_call(m.text, username)
    if replied or always:
        return True, m.text
    return False, ""

@router.message(CommandStart())
async def start(m:Message,state:FSMContext):
    await db.upsert_user(m.from_user); await state.clear(); await m.answer("🧁 <b>CakeHub AI Bot 3.3 Final</b>\n\nПросто напишите сообщение или отправьте фотографию.\n\nКоманды: /image — создать изображение, /gallery — открыть галерею.\n\nВ группе позовите меня: «КейкХаб, помоги». После вызова я буду отвечать постоянно. Отключить: /bot_off", reply_markup=ReplyKeyboardRemove())

@router.message(Command("bot_on"))
async def bot_on(m: Message):
    if _is_private(m):
        return await m.answer("В личном чате я и так отвечаю всегда.")
    await db.set_chat_always_reply(m.chat.id, True)
    await m.answer("✅ Постоянные ответы включены. Теперь я буду отвечать на сообщения в этом чате. Отключить: /bot_off")

@router.message(Command("bot_off"))
async def bot_off(m: Message):
    if _is_private(m):
        return await m.answer("В личном чате постоянный режим не отключается.")
    await db.set_chat_always_reply(m.chat.id, False)
    await m.answer("🔕 Постоянные ответы отключены. Позовите меня по имени или через @username, чтобы снова включить.")

@router.message(Command("image"))
async def image_cmd(m:Message,state:FSMContext): await state.set_state(Flow.waiting_prompt); await state.update_data(mode="generate"); await m.answer("Опишите изображение, которое нужно создать.")
@router.message(Command("gallery"))
async def gallery_cmd(m:Message): await send_gallery(m)
@router.callback_query(F.data.in_({"generate","enhance","remove_bg","analyze"}))
async def choose(c:CallbackQuery,state:FSMContext):
    mode=c.data; await state.update_data(mode=mode)
    if mode=="generate": await state.set_state(Flow.waiting_prompt); await c.message.answer("Опишите будущий дизайн.")
    else: await state.set_state(Flow.waiting_photo); await c.message.answer("Отправьте фотографию.")
    await c.answer()
@router.callback_query(F.data=="gallery")
async def gallery_cb(c:CallbackQuery): await send_gallery(c.message,c.from_user.id); await c.answer()

async def send_gallery(m:Message,user_id=None):
    rows=await db.gallery(user_id or m.from_user.id,10)
    if not rows: return await m.answer("Галерея пока пуста.")
    for p,prompt,kind in rows:
        if Path(p).exists(): await m.answer_photo(FSInputFile(p),caption=f"{kind}: {prompt[:700]}")

@router.message(Flow.waiting_photo,F.photo)
async def got_photo(m:Message,state:FSMContext,bot:Bot):
    data=await state.get_data(); mode=data.get("mode"); path=Path(settings.uploads_dir)/f"{uuid.uuid4().hex}.jpg"; await bot.download(m.photo[-1],destination=path); await state.update_data(image_path=str(path))
    if mode=="analyze":
        txt,model=await gh.analyze_image(str(path),"Проанализируй дизайн, композицию, текст, цвета и предложи конкретные улучшения."); await m.answer(f"🔍 <b>Анализ</b>\n{txt}\n\n<i>{model}</i>"); await state.clear()
    elif mode=="enhance": await enqueue_edit(m,state,"Улучши качество, резкость и детализацию изображения, сохрани композицию и все важные элементы без изменений.","enhance")
    elif mode=="remove_bg": await enqueue_edit(m,state,"Полностью удали фон, оставь основной объект аккуратно вырезанным на прозрачном фоне. Сохрани края чистыми.","remove_bg")
    else: await state.set_state(Flow.waiting_edit_prompt); await m.answer("Что нужно изменить на изображении?")

@router.message(Flow.waiting_prompt,F.text)
async def got_prompt(m:Message,state:FSMContext):
    prompt=m.text; gid=await db.create_generation(m.from_user.id,"generate",prompt)
    status=await m.answer("⏳ Добавлено в очередь…")
    async def done(path,err):
        await db.finish_generation(gid,path,str(err) if err else None)
        if err: await status.edit_text(f"❌ Ошибка: {err}")
        else: await status.delete(); await m.answer_photo(FSInputFile(path),caption="✅ Изображение готово")
    pos=await queue.submit(Job(lambda:images.generate(prompt),done)); await status.edit_text(f"⏳ Позиция в очереди: {pos}"); await state.clear()

@router.message(Flow.waiting_edit_prompt,F.text)
async def edit_prompt(m:Message,state:FSMContext): await enqueue_edit(m,state,m.text,"edit")

async def enqueue_edit(m,state,prompt,kind):
    data=await state.get_data(); path=data["image_path"]; gid=await db.create_generation(m.from_user.id,kind,prompt,path); status=await m.answer("⏳ Обработка добавлена в очередь…")
    async def done(out,err):
        await db.finish_generation(gid,out,str(err) if err else None)
        if err: await status.edit_text(f"❌ Ошибка: {err}")
        else: await status.delete(); await m.answer_photo(FSInputFile(out),caption="✅ Готово")
    pos=await queue.submit(Job(lambda:images.edit(path,prompt),done)); await status.edit_text(f"⏳ Позиция в очереди: {pos}"); await state.clear()

@router.message(F.photo)
async def generic_photo(m:Message,state:FSMContext,bot:Bot):
    path=Path(settings.uploads_dir)/f"{uuid.uuid4().hex}.jpg"; await bot.download(m.photo[-1],destination=path); await state.update_data(image_path=str(path),mode="edit"); await state.set_state(Flow.waiting_edit_prompt); await m.answer("Фото принято. Напишите, что нужно изменить на изображении.")

@router.message(F.text)
async def chat(m: Message, bot: Bot):
    should_answer, prompt = await _should_answer_group(m, bot)
    if not should_answer:
        return
    await db.upsert_user(m.from_user)
    await db.add_message(m.from_user.id, "user", prompt)
    hist = await db.get_history(m.from_user.id, settings.history_limit)
    try:
        text, model = await gh.chat(hist[:-1], prompt)
        await db.add_message(m.from_user.id, "assistant", text)
        await m.reply(text + f"\n\n<i>{model}</i>") if not _is_private(m) else await m.answer(text + f"\n\n<i>{model}</i>")
    except Exception as e:
        await m.answer(f"❌ Ошибка AI: {e}")
