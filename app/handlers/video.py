from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.keyboards import BTN_VIDEO, main_menu

router = Router(name="video")
WORK = Path("data/video_work")

SYSTEM_RULES = """IMPORTANT EDITING RULES:
Use the SOURCE VIDEO as the temporal and compositional base. Do not recreate the scene from scratch.
The user's text prompt below is the primary editing instruction.
Reference images are supplied after the source video and must be used in the same order in which the user uploaded them.
Preserve source timing, camera motion, cuts, framing, scene geometry, background, lighting, shadows, atmosphere, props and unrelated content unless the user explicitly asks to change them.
Preserve poses, gestures, expressions, head motion and gaze of replaced people unless the user explicitly asks otherwise.
Maintain photorealism and strong temporal consistency. Avoid identity drift, morphing, duplicate faces, extra people, extra limbs, geometry flicker and unintended camera changes.
"""


class VideoFlow(StatesGroup):
    prompt = State()
    source = State()
    woman = State()
    man = State()
    car = State()
    ready = State()


def _dir(uid: int) -> Path:
    p = WORK / str(uid)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _probe_dimensions(path: Path) -> tuple[int, int]:
    try:
        raw = subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", str(path)
        ], text=True)
        data = json.loads(raw); s = data["streams"][0]
        return int(s["width"]), int(s["height"])
    except Exception:
        return 0, 0


def _ratio(w: int, h: int) -> str:
    if not w or not h:
        return "9:16"
    r = w / h
    choices = {"9:16": 9/16, "16:9": 16/9, "1:1": 1, "3:4": 3/4, "4:3": 4/3, "9:21": 9/21, "21:9": 21/9}
    return min(choices, key=lambda k: abs(choices[k] - r))


async def _save(bot, file_id: str, target: Path):
    f = await bot.get_file(file_id)
    await bot.download_file(f.file_path, destination=target)


@router.message(F.text == BTN_VIDEO)
async def begin(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    d = _dir(message.from_user.id)
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    await state.clear()
    await state.set_state(VideoFlow.prompt)
    await message.answer(
        "🎬 <b>Видео AI • Seedance 2.5</b>\n\n"
        "1/5 Сначала пришлите <b>текстовый промпт</b>: что именно нужно изменить в видео.\n\n"
        "После промпта бот запросит исходное видео, затем фотографии референсов."
    )


@router.message(VideoFlow.prompt, F.text)
async def prompt(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 5:
        await message.answer("Промпт слишком короткий. Опишите задачу подробнее.")
        return
    await state.update_data(user_prompt=text)
    await state.set_state(VideoFlow.source)
    await message.answer("2/5 Теперь пришлите <b>исходное видео</b> MP4.")


@router.message(VideoFlow.source, F.video)
async def source(message: Message, state: FSMContext, bot) -> None:
    d = _dir(message.from_user.id); p = d / "source.mp4"
    await _save(bot, message.video.file_id, p)

    # Telegram already provides duration and usually width/height. This avoids
    # falling back to 5 seconds on hosts where ffprobe is not installed.
    dur = float(message.video.duration or 5)
    w = int(message.video.width or 0)
    h = int(message.video.height or 0)
    if not w or not h:
        w, h = _probe_dimensions(p)

    await state.update_data(width=w, height=h, duration=dur)
    await state.set_state(VideoFlow.woman)
    dims = f"{w}×{h}" if w and h else "размер из исходника"
    await message.answer(
        f"Видео принято: {dims}, <b>{dur:.1f} сек.</b>\n\n"
        "3/5 Пришлите <b>первое фото-референс</b> — женщина (внешность + одежда)."
    )


@router.message(VideoFlow.woman, F.photo)
async def woman(message: Message, state: FSMContext, bot) -> None:
    await _save(bot, message.photo[-1].file_id, _dir(message.from_user.id)/"woman.jpg")
    await state.set_state(VideoFlow.man)
    await message.answer("4/5 Пришлите <b>второе фото-референс</b> — мужчина.")


@router.message(VideoFlow.man, F.photo)
async def man(message: Message, state: FSMContext, bot) -> None:
    await _save(bot, message.photo[-1].file_id, _dir(message.from_user.id)/"man.jpg")
    await state.set_state(VideoFlow.car)
    await message.answer("5/5 Пришлите <b>третье фото-референс</b> — автомобиль.")


@router.message(VideoFlow.car, F.photo)
async def car(message: Message, state: FSMContext, bot) -> None:
    await _save(bot, message.photo[-1].file_id, _dir(message.from_user.id)/"car.jpg")
    await state.set_state(VideoFlow.ready)
    data = await state.get_data()
    await message.answer(
        "✅ Все материалы получены.\n\n"
        f"<b>Промпт:</b>\n{data.get('user_prompt', '')}\n\n"
        f"<b>Видео:</b> {float(data.get('duration', 5)):.1f} сек.\n"
        "<b>Референсы:</b> женщина → мужчина → автомобиль\n"
        "<b>Модель:</b> Seedance 2.5 / 720p\n\n"
        "Отправьте <b>ЗАПУСК</b> для генерации."
    )


@router.message(VideoFlow.ready, F.text.casefold() == "запуск")
async def run(message: Message, state: FSMContext, video_ai) -> None:
    d = _dir(message.from_user.id); data = await state.get_data()
    duration = max(4, min(30, round(float(data.get("duration", 5)))))
    ratio = _ratio(int(data.get("width", 0)), int(data.get("height", 0)))
    user_prompt = str(data.get("user_prompt", "")).strip()
    final_prompt = f"{SYSTEM_RULES}\nUSER EDIT INSTRUCTION:\n{user_prompt}"

    status = await message.answer(
        f"⏳ Seedance 2.5: отправляю задачу…\n"
        f"{duration} сек., {ratio}, 720p"
    )
    try:
        job = await video_ai.create(
            d/"source.mp4",
            [d/"woman.jpg", d/"man.jpg", d/"car.jpg"],
            final_prompt,
            duration=duration,
            aspect_ratio=ratio,
        )
        last = None
        async def progress(s, payload):
            nonlocal last
            if s != last:
                last = s
                try:
                    await status.edit_text(f"⏳ Seedance 2.5: {s}")
                except Exception:
                    pass
        job = await video_ai.wait(job, progress)
        if job.get("status") != "completed":
            raise RuntimeError(job.get("error") or str(job))
        out = await video_ai.download(job, d/"result.mp4")
        usage = job.get("usage") or {}
        cost = usage.get("cost_rub")
        caption = "✅ Seedance 2.5 готово."
        if cost is not None:
            caption += f"\nСтоимость: {cost} ₽"
        await message.answer_video(out, caption=caption, reply_markup=main_menu())
        await state.clear()
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        body = exc.response.text[:1500]
        if code == 402:
            text = (
                "💳 <b>Недостаточно средств на балансе AITUNNEL.</b>\n\n"
                "Seedance 2.5 не запустил генерацию. Пополните баланс и снова отправьте <b>ЗАПУСК</b>.\n"
                "Материалы и промпт сохранены в текущей сессии."
            )
        else:
            text = f"❌ AITUNNEL HTTP {code}:\n<code>{body}</code>"
        await message.answer(text, reply_markup=main_menu())
    except Exception as exc:
        await message.answer(f"❌ Ошибка Video AI:\n<code>{str(exc)[:3000]}</code>", reply_markup=main_menu())
