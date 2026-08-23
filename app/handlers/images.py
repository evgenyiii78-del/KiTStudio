from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, Message

from app.agents import get_agent
from app.database import Database
from app.keyboards import BTN_IMAGE, BTN_VISION, main_menu
from app.services.ai import AIService, AIServiceError
from app.utils import reply_long

router = Router(name="images")
logger = logging.getLogger(__name__)


class ImageFlow(StatesGroup):
    waiting_generation_prompt = State()
    waiting_analysis_photo = State()


@router.message(F.text == BTN_IMAGE)
async def image_mode(message: Message, state: FSMContext) -> None:
    await state.set_state(ImageFlow.waiting_generation_prompt)
    await message.answer(
        "Опишите картинку как можно точнее: объект, стиль, композицию, фон, цвета и текст, если он нужен."
    )


@router.message(ImageFlow.waiting_generation_prompt, F.text)
async def generate_image(message: Message, state: FSMContext, ai: AIService) -> None:
    prompt = (message.text or "").strip()
    if not prompt:
        return
    await state.clear()
    status = await message.answer("🎨 Генерирую изображение…")
    try:
        await message.bot.send_chat_action(message.chat.id, "upload_photo")
        image_bytes, mime_type, cost = await ai.generate_image(prompt)
        ext = {
            "image/jpeg": "jpg",
            "image/webp": "webp",
            "image/svg+xml": "svg",
        }.get(mime_type, "png")
        caption = "Готово."
        if cost is not None:
            caption += f" Стоимость AITunnel: {cost:.2f} ₽"
        await message.answer_document(
            BufferedInputFile(image_bytes, filename=f"cakehub_ai.{ext}"),
            caption=caption,
            reply_markup=main_menu(),
        )
    except AIServiceError as exc:
        await message.answer(f"⚠️ {exc}", parse_mode=None, reply_markup=main_menu())
    except Exception:
        logger.exception("Unhandled image generation error")
        await message.answer("⚠️ Ошибка генерации изображения. Подробности записаны в лог.", reply_markup=main_menu())
    finally:
        try:
            await status.delete()
        except Exception:
            pass


@router.message(F.text == BTN_VISION)
async def vision_mode(message: Message, state: FSMContext) -> None:
    await state.set_state(ImageFlow.waiting_analysis_photo)
    await message.answer(
        "Отправьте фото. В подписи можно написать вопрос; без подписи я подробно опишу изображение."
    )


@router.message(ImageFlow.waiting_analysis_photo, F.photo)
@router.message(F.photo)
async def analyze_photo(
    message: Message,
    state: FSMContext,
    db: Database,
    ai: AIService,
) -> None:
    if not message.from_user or not message.photo:
        return
    # В группах анализируем фото только после явного режима, чтобы не реагировать на каждую фотографию.
    current_state = await state.get_state()
    if message.chat.type != ChatType.PRIVATE and current_state != ImageFlow.waiting_analysis_photo.state:
        return

    await state.clear()
    photo = message.photo[-1]
    stream = await message.bot.download(photo)
    if stream is None:
        await message.answer("⚠️ Не удалось скачать фотографию из Telegram.", reply_markup=main_menu())
        return
    image_bytes = stream.read()
    prompt = (message.caption or "").strip() or "Подробно опиши изображение и отметь важные детали."

    agent_key = await db.get_agent_key(message.from_user.id)
    agent = get_agent(agent_key)
    system_prompt = (
        agent.system_prompt
        + "\nТы анализируешь изображение. Опирайся только на то, что действительно видно; "
          "не придумывай отсутствующие детали."
    )

    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
        answer = await ai.analyze_image(image_bytes, "image/jpeg", prompt, system_prompt)
    except AIServiceError as exc:
        await message.answer(f"⚠️ {exc}", parse_mode=None, reply_markup=main_menu())
        return
    except Exception:
        logger.exception("Unhandled vision error")
        await message.answer("⚠️ Ошибка анализа изображения. Подробности записаны в лог.", reply_markup=main_menu())
        return

    await reply_long(message, answer)
