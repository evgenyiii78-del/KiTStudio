import asyncio, base64, mimetypes
from pathlib import Path
import httpx
from app.config import settings

SYSTEM = "Ты CakeHub AI — профессиональный русскоязычный помощник кондитера. Отвечай практично, понятно и доброжелательно."

class GitHubModels:
    async def _request(self, models, messages):
        if not settings.github_token: raise RuntimeError("GITHUB_TOKEN не настроен")
        headers={"Authorization":f"Bearer {settings.github_token}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":settings.github_models_api_version}
        errors=[]
        async with httpx.AsyncClient(timeout=90) as client:
            for model in models:
                try:
                    r=await client.post(f"{settings.github_models_endpoint}/chat/completions",headers=headers,json={"model":model,"messages":messages,"temperature":0.7,"max_tokens":1500})
                    r.raise_for_status(); return r.json()["choices"][0]["message"]["content"], model
                except Exception as e:
                    errors.append(f"{model}: {e}"); await asyncio.sleep(.4)
        raise RuntimeError("Все модели недоступны: "+" | ".join(errors))

    async def chat(self, history, text):
        messages=[{"role":"system","content":SYSTEM},*history,{"role":"user","content":text}]
        return await self._request(settings.chat_models,messages)

    async def analyze_image(self, image_path, prompt):
        mime=mimetypes.guess_type(image_path)[0] or "image/jpeg"
        b64=base64.b64encode(Path(image_path).read_bytes()).decode()
        messages=[{"role":"system","content":SYSTEM},{"role":"user","content":[{"type":"text","text":prompt or "Проанализируй изображение и предложи улучшения дизайна."},{"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}}]}]
        return await self._request(settings.vision_models,messages)
