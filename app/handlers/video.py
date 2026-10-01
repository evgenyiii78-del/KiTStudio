from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.keyboards import BTN_VIDEO, main_menu

router = Router(name="video")
WORK = Path("data/video_work")

VIDEO_MODELS = {
    "🧪 Hailuo 3": {"id": "hailuo-3", "name": "Hailuo 3", "min": 5, "max": 15},
    "🧪 Flux 3 Video": {"id": "flux-3-video", "name": "Flux 3 Video", "min": 5, "max": 20},
    "🧪 Aleph 2": {"id": "aleph-2", "name": "Aleph 2", "min": 2, "max": 10},
}

SYSTEM_RULES = """STRICT SOURCE-LOCKED VIDEO EDIT.
Use the SOURCE VIDEO as the exact temporal and compositional base. Do not recreate, retime or reinterpret the scene.
The user's text prompt below is the primary editing instruction.
Reference images are supplied after the source video and must be used in this order: REFERENCE 1 = woman, REFERENCE 2 = man, REFERENCE 3 = vehicle.
Preserve source timing, camera motion, cuts, framing, perspective, scene geometry, background, lighting, shadows, atmosphere, props and unrelated content.
Preserve the exact position, motion trajectory, orientation and visibility of every existing subject/object unless the user explicitly requests its appearance to change.
For replaced people, preserve source pose, gestures, expression, head motion and gaze frame by frame while transferring only identity/appearance from the corresponding reference.
Preserve recognizable facial identity from the reference. Do not blend with the original identity, do not morph, do not create look-alikes, duplicate faces, extra people or extra limbs.
For a replaced vehicle, change appearance only; preserve its exact source position, scale, orientation, trajectory and timing frame by frame.
SOURCE VIDEO determines WHERE, WHEN and HOW everything happens. REFERENCES determine only WHAT the requested subjects LOOK LIKE.
Maintain photorealism and strong temporal consistency. No unintended camera or timing changes.
"""

class VideoFlow(StatesGroup):
    model = State(); prompt = State(); source = State(); woman = State(); man = State(); car = State(); ready = State()

def _dir(uid: int) -> Path:
    p=WORK/str(uid); p.mkdir(parents=True,exist_ok=True); return p

def _model_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=label)] for label in VIDEO_MODELS],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def _probe_dimensions(path: Path) -> tuple[int,int]:
    try:
        raw=subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","json",str(path)],text=True)
        s=json.loads(raw)["streams"][0]; return int(s["width"]),int(s["height"])
    except Exception: return 0,0

def _ratio(w:int,h:int)->str:
    if not w or not h: return "9:16"
    r=w/h; choices={"9:16":9/16,"16:9":16/9,"1:1":1,"3:4":3/4,"4:3":4/3,"9:21":9/21,"21:9":21/9}
    return min(choices,key=lambda k:abs(choices[k]-r))

async def _save(bot,file_id:str,target:Path):
    f=await bot.get_file(file_id); await bot.download_file(f.file_path,destination=target)

@router.message(F.text==BTN_VIDEO)
async def begin(message:Message,state:FSMContext)->None:
    if not message.from_user:return
    d=_dir(message.from_user.id); shutil.rmtree(d,ignore_errors=True); d.mkdir(parents=True)
    await state.clear(); await state.set_state(VideoFlow.model)
    await message.answer(
        "🎬 <b>Видео AI • тест моделей</b>\n\nВыберите модель для этого запуска:\n"
        "• Hailuo 3 — 5–15 сек.\n• Flux 3 Video — 5–20 сек.\n• Aleph 2 — 2–10 сек.",
        reply_markup=_model_keyboard(),
    )

@router.message(VideoFlow.model, F.text)
async def choose_model(message:Message,state:FSMContext)->None:
    cfg=VIDEO_MODELS.get((message.text or "").strip())
    if not cfg:
        await message.answer("Выберите модель кнопкой ниже.",reply_markup=_model_keyboard()); return
    await state.update_data(video_model=cfg["id"],video_model_name=cfg["name"],model_min=cfg["min"],model_max=cfg["max"])
    await state.set_state(VideoFlow.prompt)
    await message.answer(f"Выбрана <b>{cfg['name']}</b>.\n\n1/5 Пришлите <b>текстовый промпт</b>: что изменить в видео.")

@router.message(VideoFlow.prompt,F.text)
async def prompt(message:Message,state:FSMContext)->None:
    text=(message.text or "").strip()
    if len(text)<5: await message.answer("Промпт слишком короткий."); return
    await state.update_data(user_prompt=text); await state.set_state(VideoFlow.source)
    await message.answer("2/5 Теперь пришлите <b>исходное видео</b> MP4.")

@router.message(VideoFlow.source,F.video)
async def source(message:Message,state:FSMContext,bot)->None:
    d=_dir(message.from_user.id)
    target=d/"source.mp4"
    try:
        await _save(bot,message.video.file_id,target)
    except Exception as exc:
        await message.answer(f"❌ Не удалось скачать видео из Telegram:\n<code>{str(exc)[:1200]}</code>")
        return

    dur=float(message.video.duration or 5)
    w=int(message.video.width or 0)
    h=int(message.video.height or 0)
    if not w or not h:
        w,h=_probe_dimensions(target)

    # Hailuo / Flux / Aleph receive the original Telegram MP4 unchanged.
    # Do NOT apply the old Seedance-specific 407696-pixel check here and do
    # NOT transcode with FFmpeg. Provider-specific validation belongs to the
    # provider adapter, not to the common upload flow.
    data=await state.get_data()
    model=data.get("video_model","hailuo-3")
    await state.update_data(width=w,height=h,duration=dur,prepared=False)
    await state.set_state(VideoFlow.woman)
    dims=f"{w}×{h}" if w and h else "размер не определён"
    await message.answer(
        f"Видео принято без перекодирования: <b>{dims}</b>, <b>{dur:.1f} сек.</b>\n"
        f"Модель: <b>{data.get('video_model_name',model)}</b>\n\n"
        "3/5 Пришлите <b>первое фото</b> — женщина (внешность + одежда)."
    )

@router.message(VideoFlow.woman,F.photo)
async def woman(message:Message,state:FSMContext,bot)->None:
    await _save(bot,message.photo[-1].file_id,_dir(message.from_user.id)/"woman.jpg"); await state.set_state(VideoFlow.man); await message.answer("4/5 Пришлите <b>второе фото</b> — мужчина.")

@router.message(VideoFlow.man,F.photo)
async def man(message:Message,state:FSMContext,bot)->None:
    await _save(bot,message.photo[-1].file_id,_dir(message.from_user.id)/"man.jpg"); await state.set_state(VideoFlow.car); await message.answer("5/5 Пришлите <b>третье фото</b> — автомобиль.")

@router.message(VideoFlow.car,F.photo)
async def car(message:Message,state:FSMContext,bot)->None:
    await _save(bot,message.photo[-1].file_id,_dir(message.from_user.id)/"car.jpg"); await state.set_state(VideoFlow.ready); data=await state.get_data()
    max_d=int(data.get("model_max",15)); original_d=float(data.get("duration",5)); send_d=max(int(data.get("model_min",5)),min(max_d,round(original_d)))
    trim_note=f"\n⚠️ Для этой модели будет отправлено максимум <b>{max_d} сек.</b>" if original_d>max_d else ""
    await message.answer("✅ Все материалы получены.\n\n"+f"<b>Промпт:</b>\n{data.get('user_prompt','')}\n\n<b>Видео:</b> {original_d:.1f} сек., {data.get('width')}×{data.get('height')}\n<b>Референсы:</b> женщина → мужчина → автомобиль\n<b>Модель:</b> {data.get('video_model_name','Hailuo 3')}\n<b>Длительность запроса:</b> {send_d} сек.{trim_note}\n\nОтправьте <b>ЗАПУСК</b>.")

@router.message(VideoFlow.ready,F.text.casefold()=="запуск")
async def run(message:Message,state:FSMContext,video_ai)->None:
    d=_dir(message.from_user.id); data=await state.get_data()
    model=str(data.get("video_model","hailuo-3")); model_name=str(data.get("video_model_name","Hailuo 3"))
    min_d=int(data.get("model_min",5)); max_d=int(data.get("model_max",15)); duration=max(min_d,min(max_d,round(float(data.get("duration",5)))))
    ratio=_ratio(int(data.get("width",0)),int(data.get("height",0)))
    final_prompt=f"{SYSTEM_RULES}\nUSER EDIT INSTRUCTION:\n{str(data.get('user_prompt','')).strip()}"
    status=await message.answer(f"⏳ {model_name}: отправляю задачу…\n{duration} сек., {ratio}")
    try:
        job=await video_ai.create(d/"source.mp4",[d/"woman.jpg",d/"man.jpg",d/"car.jpg"],final_prompt,model=model,duration=duration,aspect_ratio=ratio)
        last=None
        async def progress(s,payload):
            nonlocal last
            if s!=last:
                last=s
                try: await status.edit_text(f"⏳ {model_name}: {s}")
                except Exception: pass
        job=await video_ai.wait(job,progress)
        if job.get("status")!="completed": raise RuntimeError(job.get("error") or str(job))
        out=await video_ai.download(job,d/"result.mp4"); cost=(job.get("usage") or {}).get("cost_rub")
        caption=f"✅ {model_name} готово."+(f"\nСтоимость: {cost} ₽" if cost is not None else "")
        await message.answer_video(out,caption=caption,reply_markup=main_menu()); await state.clear()
    except httpx.HTTPStatusError as exc:
        code=exc.response.status_code; body=exc.response.text[:2200]
        if code==402: text="💳 <b>Недостаточно средств на балансе AITUNNEL.</b>\nМатериалы сохранены. После пополнения снова отправьте <b>ЗАПУСК</b>."
        else: text=f"❌ {model_name} / AITUNNEL HTTP {code}:\n<code>{body}</code>"
        await message.answer(text,reply_markup=main_menu())
    except Exception as exc:
        await message.answer(f"❌ Ошибка {model_name}:\n<code>{str(exc)[:3000]}</code>",reply_markup=main_menu())
