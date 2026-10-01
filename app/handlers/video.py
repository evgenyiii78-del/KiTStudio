from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.keyboards import BTN_VIDEO, main_menu

router = Router(name="video")
WORK = Path("data/video_work")

PROMPT = """EDIT THE SOURCE VIDEO. Do not recreate the scene from scratch.
REFERENCE 1 = WOMAN identity and clothing. REFERENCE 2 = MAN identity. REFERENCE 3 = REPLACEMENT CAR.
Exactly two humans only. Replace the seated woman throughout with reference 1, preserving her identity, face, hairstyle and clothing while transferring the source woman's exact pose, gestures, expression, head motion and gaze. Replace the man inside the car with reference 2; preserve the original driver's exact position, occlusion and visibility and never make his face clearer, larger, closer or more exposed. Replace only the black car with reference 3, preserving trajectory, position, scale, perspective, orientation, wheel motion and timing. STRICT: preserve source camera, cuts, timing, framing, background, lighting, shadows, atmosphere, props and unrelated content. Strong temporal consistency. Never restore original actors, swap identities, add people, morph faces, add limbs or alter camera angle."""


class VideoFlow(StatesGroup):
    source = State()
    woman = State()
    man = State()
    car = State()
    ready = State()


def _dir(uid: int) -> Path:
    p = WORK / str(uid)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _probe(path: Path) -> tuple[int, int, float]:
    try:
        raw = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path)], text=True)
        data = json.loads(raw); s = data["streams"][0]
        return int(s["width"]), int(s["height"]), float(data["format"]["duration"])
    except Exception:
        return 720, 1280, 5.0


def _ratio(w: int, h: int) -> str:
    r = w / h
    choices = {"9:16": 9/16, "16:9": 16/9, "1:1": 1, "3:4": 3/4, "4:3": 4/3, "9:21": 9/21, "21:9": 21/9}
    return min(choices, key=lambda k: abs(choices[k] - r))


async def _save(bot, file_id: str, target: Path):
    f = await bot.get_file(file_id)
    await bot.download_file(f.file_path, destination=target)


@router.message(F.text == BTN_VIDEO)
async def begin(message: Message, state: FSMContext) -> None:
    if not message.from_user: return
    d = _dir(message.from_user.id); shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
    await state.clear(); await state.set_state(VideoFlow.source)
    await message.answer("🎬 <b>Видео AI</b>\n\n1/4 Пришлите исходное видео MP4.")


@router.message(VideoFlow.source, F.video)
async def source(message: Message, state: FSMContext, bot) -> None:
    d = _dir(message.from_user.id); p = d / "source.mp4"
    await _save(bot, message.video.file_id, p)
    w, h, dur = _probe(p); await state.update_data(width=w, height=h, duration=dur)
    await state.set_state(VideoFlow.woman)
    await message.answer(f"Видео: {w}×{h}, {dur:.1f} сек.\n2/4 Пришлите фото женщины (внешность + одежда).")


@router.message(VideoFlow.woman, F.photo)
async def woman(message: Message, state: FSMContext, bot) -> None:
    await _save(bot, message.photo[-1].file_id, _dir(message.from_user.id)/"woman.jpg")
    await state.set_state(VideoFlow.man); await message.answer("3/4 Пришлите фото мужчины.")


@router.message(VideoFlow.man, F.photo)
async def man(message: Message, state: FSMContext, bot) -> None:
    await _save(bot, message.photo[-1].file_id, _dir(message.from_user.id)/"man.jpg")
    await state.set_state(VideoFlow.car); await message.answer("4/4 Пришлите фото автомобиля.")


@router.message(VideoFlow.car, F.photo)
async def car(message: Message, state: FSMContext, bot) -> None:
    await _save(bot, message.photo[-1].file_id, _dir(message.from_user.id)/"car.jpg")
    await state.set_state(VideoFlow.ready)
    await message.answer("Все референсы получены. Отправьте <b>ЗАПУСК</b> для генерации Seedance 2.5.")


@router.message(VideoFlow.ready, F.text.casefold() == "запуск")
async def run(message: Message, state: FSMContext, video_ai) -> None:
    d = _dir(message.from_user.id); data = await state.get_data()
    duration = max(4, min(30, round(float(data.get("duration", 5)))))
    ratio = _ratio(int(data.get("width", 720)), int(data.get("height", 1280)))
    status = await message.answer(f"⏳ Seedance 2.5: отправляю задачу…\n{duration} сек., {ratio}, 720p")
    try:
        job = await video_ai.create(d/"source.mp4", [d/"woman.jpg", d/"man.jpg", d/"car.jpg"], PROMPT, duration=duration, aspect_ratio=ratio)
        last = None
        async def progress(s, payload):
            nonlocal last
            if s != last:
                last = s
                try: await status.edit_text(f"⏳ Seedance 2.5: {s}")
                except Exception: pass
        job = await video_ai.wait(job, progress)
        if job.get("status") != "completed": raise RuntimeError(job.get("error") or str(job))
        out = await video_ai.download(job, d/"result.mp4")
        await message.answer_video(out, caption="✅ Seedance 2.5 готово.", reply_markup=main_menu())
        await state.clear()
    except Exception as exc:
        await message.answer(f"❌ Ошибка Video AI:\n<code>{str(exc)[:3000]}</code>", reply_markup=main_menu())
