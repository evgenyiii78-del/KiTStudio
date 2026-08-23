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


async def _generate(message: Message, state: FSMContext, ai: AIService, prompt: str) -> None:
    prompt = prompt.strip()
    if not prompt:
        return

    await state.clear()
    status = await message.answer("🎨 Генерирую изображение через gpt-image-2…")

    try:
        await message.bot.send_chat_action(message.chat.id, "upload_photo")
        image_bytes, mime_type, cost = await ai.generate_image(prompt)

        ext = {
            "image/jpeg": "jpg",
            "image/webp": "webp",
        }.get(mime_type, "png")

        caption = "✅ Готово"
        if cost is not None:
            caption += f" · {cost:.2f} ₽"

        await message.answer_photo(
            photo=BufferedInputFile(image_bytes, filename=f"kitstudio_ai.{ext}"),
            caption=caption,
            reply_markup=main_menu(),
        )
    except AIServiceError as exc:
        await message.answer(f"⚠️ {exc}", parse_mode=None, reply_markup=main_menu())
    except Exception:
        logger.exception("Unhandled image generation error")
        await message.answer(
            "⚠️ Не удалось создать изображение. Подробности записаны в лог.",
            reply_markup=main_menu(),
        )
    finally:
        try:
            await status.delete()
        except Exception:
            pass


@router.message(F.text == BTN_IMAGE)
async def image_mode(message: Message, state: FSMContext) -> None:
    await state.set_state(ImageFlow.waiting_generation_prompt)
    await message.answer(
        "Опишите изображение одним сообщением.\n\n"
        "Например: «Белый бенто-торт, минималистичный рисунок чёрного кота, "
        "вид спереди, белый фон, надпись “ну с др”»."
    )


@router.message(ImageFlow.waiting_generation_prompt, F.text)
async def generation_prompt(message: Message, state: FSMContext, ai: AIService) -> None:
    await _generate(message, state, ai, message.text or "")


@router.message(F.chat.type == ChatType.PRIVATE, F.text)
async def direct_prompt(message: Message, state: FSMContext, ai: AIService) -> None:
    await _generate(message, state, ai, message.text or "")


@router.message(F.chat.type == ChatType.PRIVATE, F.photo)
async def photo_received(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Я сейчас работаю как генератор изображений. Напишите текстом, что нужно создать.",
        reply_markup=main_menu(),
    )
