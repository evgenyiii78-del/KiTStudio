import asyncio, base64, mimetypes
from pathlib import Path
import httpx
from app.config import settings

BASE_SYSTEM = "Ты CakeHub AI — профессиональный русскоязычный помощник. Отвечай практично, понятно и доброжелательно."

AGENT_PROMPTS = {
    "universal": "Ты универсальный AI-помощник CakeHub. Помогай с любыми вопросами, особенно связанными с кондитерским делом, бизнесом и технологиями.",
    "confectioner": "Ты опытный шеф-кондитер. Помогай с рецептами, технологией приготовления, начинками, кремами, хранением, себестоимостью и устранением ошибок. Давай точные и безопасные рекомендации.",
    "designer": "Ты дизайнер тортов и бенто-десертов. Помогай с композицией, цветами, надписями, декором, фотопечатью и промптами для генерации изображений. Предлагай конкретные визуальные решения.",
    "marketing": "Ты маркетолог кондитерского бизнеса. Помогай с ценами, карточками товаров, объявлениями, продвижением, контентом, продажами и анализом спроса. Делай рекомендации применимыми на практике.",
    "technical": "Ты технический помощник CakeHub. Помогай с Telegram-ботами, Python, Docker, Railway, API, 3D-печатью и настройкой оборудования. Давай проверяемые пошаговые инструкции и рабочие примеры кода.",
}

class GitHubModels:
    async def _request(self, models, messages):
        if not settings.github_token:
            raise RuntimeError("GITHUB_TOKEN не настроен")
        headers={"Authorization":f"Bearer {settings.github_token}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":settings.github_models_api_version}
        errors=[]
        async with httpx.AsyncClient(timeout=90) as client:
            for model in models:
                try:
                    r=await client.post(f"{settings.github_models_endpoint}/chat/completions",headers=headers,json={"model":model,"messages":messages,"temperature":0.7,"max_tokens":1500})
                    r.raise_for_status()
                    return r.json()["choices"][0]["message"]["content"], model
                except Exception as e:
                    errors.append(f"{model}: {e}")
                    await asyncio.sleep(.4)
        raise RuntimeError("Все модели недоступны: "+" | ".join(errors))

    async def chat(self, history, text, agent="universal"):
        agent_prompt = AGENT_PROMPTS.get(agent, AGENT_PROMPTS["universal"])
        messages=[{"role":"system","content":f"{BASE_SYSTEM}\n\nТекущая роль:\n{agent_prompt}"},*history,{"role":"user","content":text}]
        return await self._request(settings.chat_models,messages)

    async def analyze_image(self, image_path, prompt, agent="designer"):
        mime=mimetypes.guess_type(image_path)[0] or "image/jpeg"
        b64=base64.b64encode(Path(image_path).read_bytes()).decode()
        agent_prompt = AGENT_PROMPTS.get(agent, AGENT_PROMPTS["designer"])
        messages=[{"role":"system","content":f"{BASE_SYSTEM}\n\nТекущая роль:\n{agent_prompt}"},{"role":"user","content":[{"type":"text","text":prompt or "Проанализируй изображение и предложи улучшения дизайна."},{"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}}]}]
        return await self._request(settings.vision_models,messages)
