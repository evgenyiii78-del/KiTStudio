from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile
from app.keyboards import BTN_IMAGE, BTN_ANALYZE, main_keyboard
from app.states import ImageStates

router=Router()

@router.message(Command("image"))
@router.message(F.text==BTN_IMAGE)
async def image_start(message:Message,state:FSMContext):
    await state.set_state(ImageStates.waiting_prompt)
    await message.answer("Опишите изображение, которое нужно создать:")

@router.message(ImageStates.waiting_prompt,F.text)
async def image_prompt(message:Message,state:FSMContext,ai):
    status=await message.answer("🎨 Создаю изображение…")
    try:
        path=await ai.generate_image(message.text)
        await message.answer_photo(FSInputFile(path),caption="Готово.",reply_markup=main_keyboard)
    except Exception as e:
        await message.answer(f"❌ Ошибка генерации: <code>{str(e)[:700]}</code>",reply_markup=main_keyboard)
    finally:
        await status.delete(); await state.clear()

@router.message(F.text==BTN_ANALYZE)
async def analyze_start(message:Message,state:FSMContext):
    await state.set_state(ImageStates.waiting_analysis_photo)
    await message.answer("Отправьте фотографию. Я проанализирую её выбранным агентом.")

@router.message(ImageStates.waiting_analysis_photo,F.photo)
async def analyze_photo(message:Message,state:FSMContext,bot,ai,db):
    status=await message.answer("🔍 Анализирую фотографию…")
    try:
        f=await bot.get_file(message.photo[-1].file_id)
        stream=await bot.download_file(f.file_path)
        agent=await db.get_agent(message.chat.id,message.from_user.id)
        text=await ai.analyze_image(stream.read(),"Подробно проанализируй изображение и дай полезные рекомендации.",agent)
        await message.answer(text,reply_markup=main_keyboard)
    except Exception as e:
        await message.answer(f"❌ Ошибка анализа: <code>{str(e)[:700]}</code>",reply_markup=main_keyboard)
    finally:
        await status.delete(); await state.clear()

@router.message(ImageStates.waiting_analysis_photo)
async def need_photo(message:Message): await message.answer("Нужно отправить именно фотографию.")
