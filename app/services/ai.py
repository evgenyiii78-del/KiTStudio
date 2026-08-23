from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class AIServiceError(RuntimeError):
    pass


class AIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._image_sem = asyncio.Semaphore(1)
        self._client = httpx.AsyncClient(
            base_url=settings.aitunnel_base_url,
            headers={"Authorization": f"Bearer {settings.aitunnel_api_key}"},
            timeout=httpx.Timeout(settings.ai_timeout_seconds),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(path, json=payload)
        except httpx.TimeoutException as exc:
            raise AIServiceError("AITunnel не ответил вовремя. Попробуйте ещё раз.") from exc
        except httpx.HTTPError as exc:
            raise AIServiceError(f"Ошибка соединения с AITunnel: {exc}") from exc

        if response.is_error:
            detail = response.text[:1200]
            logger.error("AITunnel %s on %s: %s", response.status_code, path, detail)
            try:
                body = response.json()
                error = body.get("error")
                if isinstance(error, dict):
                    detail = str(error.get("message") or error.get("code") or detail)
                elif error:
                    detail = str(error)
            except Exception:
                pass
            raise AIServiceError(f"AITunnel вернул ошибку {response.status_code}: {detail}")

        try:
            return response.json()
        except ValueError as exc:
            raise AIServiceError("AITunnel вернул некорректный JSON.") from exc

    @staticmethod
    def _decode_image_response(data: dict[str, Any], default_format: str) -> tuple[bytes, str, float | None]:
        try:
            item = data["data"][0]
            raw = base64.b64decode(item["b64_json"])
            mime = item.get("media_type") or f"image/{default_format}"
            usage = data.get("usage") or {}
            cost = usage.get("cost_rub")
            return raw, str(mime), float(cost) if cost is not None else None
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.error("Unexpected image response: %r", data)
            raise AIServiceError("Не удалось разобрать изображение из ответа AITunnel.") from exc

    async def generate_image(self, prompt: str) -> tuple[bytes, str, float | None]:
        payload: dict[str, Any] = {
            "model": "gpt-image-2",
            "prompt": prompt,
            "n": 1,
            "size": self.settings.image_size,
            "quality": self.settings.image_quality,
            "output_format": self.settings.image_output_format,
        }
        async with self._image_sem:
            data = await self._post_json("/images/generations", payload)
        return self._decode_image_response(data, self.settings.image_output_format)

    async def edit_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
    ) -> tuple[bytes, str, float | None]:
        filename = "source.png" if mime_type == "image/png" else "source.jpg"
        files = {"image": (filename, image_bytes, mime_type)}
        form = {
            "model": "gpt-image-2",
            "prompt": prompt,
            "n": "1",
            "size": self.settings.image_size,
            "quality": self.settings.image_quality,
            "output_format": self.settings.image_output_format,
        }
        try:
            async with self._image_sem:
                response = await self._client.post("/images/edits", data=form, files=files)
        except httpx.TimeoutException as exc:
            raise AIServiceError("AITunnel не ответил вовремя при редактировании изображения.") from exc
        except httpx.HTTPError as exc:
            raise AIServiceError(f"Ошибка соединения с AITunnel: {exc}") from exc

        if response.is_error:
            detail = response.text[:1200]
            logger.error("AITunnel %s on /images/edits: %s", response.status_code, detail)
            try:
                body = response.json()
                error = body.get("error")
                if isinstance(error, dict):
                    detail = str(error.get("message") or detail)
            except Exception:
                pass
            raise AIServiceError(f"AITunnel вернул ошибку {response.status_code}: {detail}")

        try:
            data = response.json()
        except ValueError as exc:
            raise AIServiceError("AITunnel вернул некорректный JSON при редактировании.") from exc
        return self._decode_image_response(data, self.settings.image_output_format)
