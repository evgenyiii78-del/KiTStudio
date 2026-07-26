from __future__ import annotations
import base64, uuid
from pathlib import Path
import httpx
from openai import AsyncOpenAI
from app.agents import AGENTS

class AIService:
    def __init__(self, settings):
        self.s=settings
        self.client=AsyncOpenAI(api_key=settings.aitunnel_api_key, base_url=settings.aitunnel_base_url)

    async def chat(self, history:list[dict], text:str, agent_key:str) -> str:
        system=AGENTS.get(agent_key,AGENTS['universal'])[1]
        messages=[{"role":"system","content":system},*history,{"role":"user","content":text}]
        r=await self.client.chat.completions.create(model=self.s.chat_model,messages=messages,temperature=0.7)
        return (r.choices[0].message.content or "Не удалось получить ответ.").strip()

    async def analyze_image(self, image:bytes, prompt:str, agent_key:str) -> str:
        b64=base64.b64encode(image).decode()
        system=AGENTS.get(agent_key,AGENTS['universal'])[1]
        messages=[{"role":"system","content":system},{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}]
        r=await self.client.chat.completions.create(model=self.s.vision_model,messages=messages,max_tokens=1200)
        return (r.choices[0].message.content or "Не удалось проанализировать фото.").strip()

    async def generate_image(self,prompt:str) -> Path:
        kwargs={"model":self.s.image_model,"prompt":prompt,"size":self.s.image_size,"n":1}
        if self.s.image_quality: kwargs["quality"]=self.s.image_quality
        r=await self.client.images.generate(**kwargs)
        item=r.data[0]
        out=self.s.generated_dir/f"{uuid.uuid4().hex}.png"
        if getattr(item,"b64_json",None): out.write_bytes(base64.b64decode(item.b64_json)); return out
        if getattr(item,"url",None):
            async with httpx.AsyncClient(timeout=120) as client:
                resp=await client.get(item.url); resp.raise_for_status(); out.write_bytes(resp.content); return out
        raise RuntimeError("AITunnel не вернул изображение")
