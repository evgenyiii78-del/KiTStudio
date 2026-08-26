from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, Message

from app.keyboards import BTN_IMAGE, main_menu
from app.services.ai import AIService, AIServiceError

router = Router(name="images")
logger = logging.getLogger(__name__)


class ImageFlow(StatesGroup):
    waiting_generation_prompt = State()
    waiting_edit_instruction = State()


def _reply_markup(message: Message):
    return main_menu() if message.chat.type == ChatType.PRIVATE else None


async def _send(message: Message, text: str, **kwargs):
    if message.chat.type == ChatType.PRIVATE:
        return await message.answer(text, **kwargs)
    return await message.reply(text, **kwargs)


async def _generate(message: Message, state: FSMContext, ai: AIService, prompt: str) -> None:
    prompt = prompt.strip()
    if not prompt:
        return
    await state.clear()
    logger.info("IMAGE GENERATE -> | chat=%s user=%s prompt=%r", message.chat.id, message.from_user.id if message.from_user else None, prompt[:500])
    status = await _send(message, "🎨 Генерирую изображение через gpt-image-2…")
    try:
        await message.bot.send_chat_action(message.chat.id, "upload_photo")
        image_bytes, mime_type, cost = await ai.generate_image(prompt)
        logger.info("IMAGE GENERATE <- | bytes=%s mime=%s cost=%s", len(image_bytes), mime_type, cost)
        ext = {"image/jpeg": "jpg", "image/webp": "webp"}.get(mime_type, "png")
        caption = "✅ Готово"
        if cost is not None:
            caption += f" · {cost:.2f} ₽"
        kwargs = dict(photo=BufferedInputFile(image_bytes, filename=f"kitstudio_ai.{ext}"), caption=caption, reply_markup=_reply_markup(message))
        if message.chat.type == ChatType.PRIVATE:
            await message.answer_photo(**kwargs)
        else:
            await message.reply_photo(**kwargs)
    except AIServiceError as exc:
        logger.warning("IMAGE GENERATE ERROR | %s", exc)
        await _send(message, f"⚠️ {exc}", parse_mode=None, reply_markup=_reply_markup(message))
    except Exception:
        logger.exception("Unhandled image generation error")
        await _send(message, "⚠️ Не удалось создать изображение. Подробности записаны в лог.", reply_markup=_reply_markup(message))
    finally:
        try:
            await status.delete()
        except Exception:
            pass


@router.message(F.text == BTN_IMAGE)
async def image_mode(message: Message, state: FSMContext) -> None:
    await state.set_state(ImageFlow.waiting_generation_prompt)
    await _send(message, "Опишите изображение одним сообщением.\n\nНапример: «Белый бенто-торт, минималистичный рисунок чёрного кота, вид спереди, белый фон».")


@router.message(ImageFlow.waiting_generation_prompt, F.text)
async def generation_prompt(message: Message, state: FSMContext, ai: AIService) -> None:
    await _generate(message, state, ai, message.text or "")


@router.message(ImageFlow.waiting_edit_instruction, F.text)
async def edit_instruction(message: Message, state: FSMContext, ai: AIService) -> None:
    data = await state.get_data()
    file_id = data.get("edit_photo_file_id")
    instruction = (message.text or "").strip()
    logger.info("IMAGE EDIT INSTRUCTION | chat=%s user=%s file=%s instruction=%r", message.chat.id, message.from_user.id if message.from_user else None, bool(file_id), instruction[:500])
    if not file_id or not instruction:
        await state.clear()
        await _send(message, "⚠️ Не удалось получить исходное изображение. Загрузите его ещё раз.", reply_markup=_reply_markup(message))
        return

    status = await _send(message, "🖌 Редактирую загруженное изображение…")
    try:
        logger.info("TELEGRAM IMAGE -> download file_id=%s...", file_id[:20])
        tg_file = await message.bot.get_file(file_id)
        downloaded = await message.bot.download_file(tg_file.file_path)
        source_bytes = downloaded.read()
        logger.info("TELEGRAM IMAGE <- bytes=%s path=%s", len(source_bytes), tg_file.file_path)
        await message.bot.send_chat_action(message.chat.id, "upload_photo")
        logger.info("AI IMAGE EDIT -> | bytes=%s instruction=%r", len(source_bytes), instruction[:500])
        image_bytes, mime_type, cost = await ai.edit_image(source_bytes, "image/jpeg", instruction)
        logger.info("AI IMAGE EDIT <- | bytes=%s mime=%s cost=%s", len(image_bytes), mime_type, cost)
        ext = {"image/jpeg": "jpg", "image/webp": "webp"}.get(mime_type, "png")
        caption = "✅ Готово"
        if cost is not None:
            caption += f" · {cost:.2f} ₽"
        kwargs = dict(photo=BufferedInputFile(image_bytes, filename=f"kitstudio_edit.{ext}"), caption=caption, reply_markup=_reply_markup(message))
        if message.chat.type == ChatType.PRIVATE:
            await message.answer_photo(**kwargs)
        else:
            await message.reply_photo(**kwargs)
        logger.info("IMAGE EDIT DONE | chat=%s user=%s", message.chat.id, message.from_user.id if message.from_user else None)
    except AIServiceError as exc:
        logger.warning("AI IMAGE EDIT ERROR | chat=%s user=%s error=%s", message.chat.id, message.from_user.id if message.from_user else None, exc)
        await _send(message, f"⚠️ {exc}", parse_mode=None, reply_markup=_reply_markup(message))
    except Exception:
        logger.exception("Unhandled image edit error")
        await _send(message, "⚠️ Не удалось отредактировать изображение. Подробности записаны в лог.", reply_markup=_reply_markup(message))
    finally:
        await state.clear()
        try:
            await status.delete()
        except Exception:
            pass


@router.message(F.photo)
async def photo_received(message: Message, state: FSMContext) -> None:
    logger.info("TG PHOTO | chat=%s type=%s user=%s msg=%s sizes=%s caption=%r", message.chat.id, message.chat.type, message.from_user.id if message.from_user else None, message.message_id, len(message.photo or []), (message.caption or "")[:500])
    await state.clear()
    if not message.photo:
        return
    file_id = message.photo[-1].file_id
    await state.update_data(edit_photo_file_id=file_id)
    await state.set_state(ImageFlow.waiting_edit_instruction)
    logger.info("FSM | chat=%s user=%s -> waiting_edit_instruction file_id=%s...", message.chat.id, message.from_user.id if message.from_user else None, file_id[:20])
    await _send(message,
        "🖼 Изображение загружено.\n\n"
        "Что с ним сделать? Ответьте на это сообщение обычным текстом.\n\n"
        "Например:\n"
        "• вставь картинку в круг\n"
        "• удали фон\n"
        "• убери текст\n"
        "• сделай белый фон\n"
        "• добавь надпись «С Днём рождения»")


@router.message(F.chat.type == ChatType.PRIVATE, F.text)
async def direct_prompt(message: Message, state: FSMContext, ai: AIService) -> None:
    await _generate(message, state, ai, message.text or "")
