import base64, uuid
from pathlib import Path
from openai import AsyncOpenAI
from app.config import settings

class ImageService:
    def __init__(self):
        self.client=AsyncOpenAI(api_key=settings.aitunnel_api_key,base_url=settings.aitunnel_base_url)

    def _save(self,b64):
        path=Path(settings.generated_dir)/f"{uuid.uuid4().hex}.png"; path.write_bytes(base64.b64decode(b64)); return str(path)

    async def generate(self,prompt):
        if not settings.aitunnel_api_key: raise RuntimeError("AITUNNEL_API_KEY не настроен")
        r=await self.client.images.generate(model=settings.aitunnel_image_model,prompt=prompt,size=settings.image_size,quality=settings.image_quality,n=1)
        return self._save(r.data[0].b64_json)

    async def edit(self,image_path,prompt):
        if not settings.aitunnel_api_key: raise RuntimeError("AITUNNEL_API_KEY не настроен")
        with open(image_path,"rb") as f:
            r=await self.client.images.edit(model=settings.aitunnel_image_model,image=f,prompt=prompt,size=settings.image_size,n=1)
        return self._save(r.data[0].b64_json)
