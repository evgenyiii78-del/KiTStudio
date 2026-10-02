from __future__ import annotations

import asyncio
import base64
import mimetypes
from pathlib import Path

import httpx

TERMINAL = {"completed", "failed", "expired", "cancelled"}


def _data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


class VideoAIService:
    def __init__(self, settings):
        self.settings = settings
        self.base_url = settings.aitunnel_base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {settings.aitunnel_api_key}"}

    async def create(self, source_video: Path, references: list[Path], prompt: str,
                     model: str = "seedance-2.0-mini", duration: int = 5,
                     aspect_ratio: str = "9:16") -> dict:
        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "input_references": [
                {"type": "video_url", "video_url": {"url": _data_url(source_video)}},
                *[{"type": "image_url", "image_url": {"url": _data_url(p)}} for p in references],
            ],
        }

        if model == "seedance-2.0-mini":
            payload["resolution"] = "480p"
            payload["aspect_ratio"] = aspect_ratio
        elif model == "seedance-2.5":
            payload["resolution"] = "720p"
            payload["aspect_ratio"] = aspect_ratio
        elif model == "flux-3-video":
            payload["resolution"] = "720p"
            payload["aspect_ratio"] = aspect_ratio
        elif model == "aleph-2":
            payload["aspect_ratio"] = aspect_ratio

        async with httpx.AsyncClient(timeout=240) as client:
            r = await client.post(
                f"{self.base_url}/videos",
                headers=self.headers,
                json=payload,
            )
            r.raise_for_status()
            return r.json()

    async def wait(self, job: dict, callback=None) -> dict:
        url = job.get("polling_url") or f"{self.base_url}/videos/{job['id']}"
        async with httpx.AsyncClient(timeout=60) as client:
            while True:
                r = await client.get(url, headers=self.headers)
                r.raise_for_status()
                job = r.json()
                status = job.get("status", "unknown")
                if callback:
                    await callback(status, job)
                if status in TERMINAL:
                    return job
                await asyncio.sleep(self.settings.video_poll_seconds)

    async def download(self, job: dict, target: Path) -> Path:
        urls = job.get("unsigned_urls") or job.get("urls") or []
        if urls:
            url, headers = urls[0], {}
        else:
            url = f"{self.base_url}/videos/{job['id']}/content?index=0"
            headers = self.headers
        async with httpx.AsyncClient(timeout=600, follow_redirects=True) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            target.write_bytes(r.content)
        return target
