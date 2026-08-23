from __future__ import annotations

import asyncio
import base64
import logging
import re
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class AIServiceError(RuntimeError):
    pass


class AIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._chat_sem = asyncio.Semaphore(4)
        self._image_sem = asyncio.Semaphore(1)
        self._client = httpx.AsyncClient(
            base_url=settings.aitunnel_base_url,
            headers={
                "Authorization": f"Bearer {settings.aitunnel_api_key}",
                "Content-Type": "application/json",
            },
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
            logger.error("AITunnel %s: %s", response.status_code, detail)
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

    async def chat(self, messages: list[dict[str, Any]], system_prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.settings.chat_model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "max_tokens": self.settings.max_output_tokens,
        }
        async with self._chat_sem:
            data = await self._post_json("/chat/completions", payload)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected chat response: %r", data)
            raise AIServiceError("Не удалось разобрать ответ AI.") from exc
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            texts = [str(item.get("text", "")) for item in content if isinstance(item, dict)]
            return "\n".join(filter(None, texts)).strip()
        return str(content).strip()

    async def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        system_prompt: str,
    ) -> str:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        payload: dict[str, Any] = {
            "model": self.settings.vision_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                        },
                    ],
                },
            ],
            "max_tokens": self.settings.max_output_tokens,
        }
        async with self._chat_sem:
            data = await self._post_json("/chat/completions", payload)
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected vision response: %r", data)
            raise AIServiceError("Не удалось разобрать ответ анализа изображения.") from exc

    @staticmethod
    def _preferred_image_model(configured_model: str) -> str:
        # AITunnel does not guarantee that the virtual model `auto` is enabled
        # for image-generation API keys. Use a real image model by default.
        model = (configured_model or "").strip()
        if not model or model.lower() == "auto":
            return "gpt-image-2"
        return model

    @staticmethod
    def _allowed_models_from_error(message: str) -> list[str]:
        # Typical AITunnel 403 text:
        # "... Разрешённые: gemini-3.1-flash-lite-image, gpt-image-2."
        match = re.search(r"Разреш[её]нные\s*:\s*([^\n]+)", message, flags=re.IGNORECASE)
        if not match:
            return []
        raw = match.group(1).strip().rstrip(".")
        result: list[str] = []
        for item in raw.split(","):
            model = item.strip().strip("`'\"")
            if model and re.fullmatch(r"[A-Za-z0-9._/-]+", model):
                result.append(model)
        return result

    async def generate_image(self, prompt: str) -> tuple[bytes, str, float | None]:
        model = self._preferred_image_model(self.settings.image_model)
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": self.settings.image_size,
            "quality": self.settings.image_quality,
            "output_format": self.settings.image_output_format,
        }

        async with self._image_sem:
            try:
                data = await self._post_json("/images/generations", payload)
            except AIServiceError as exc:
                allowed = self._allowed_models_from_error(str(exc))
                if not allowed:
                    raise

                # Prefer GPT Image 2 when the current key permits it; otherwise
                # use the first image model explicitly returned by AITunnel.
                fallback = "gpt-image-2" if "gpt-image-2" in allowed else allowed[0]
                if fallback == model:
                    raise

                logger.warning(
                    "AITunnel rejected image model %s; retrying with permitted model %s",
                    model,
                    fallback,
                )
                payload["model"] = fallback
                data = await self._post_json("/images/generations", payload)

        try:
            item = data["data"][0]
            raw = base64.b64decode(item["b64_json"])
            mime = item.get("media_type") or f"image/{self.settings.image_output_format}"
            usage = data.get("usage") or {}
            cost = usage.get("cost_rub")
            return raw, str(mime), float(cost) if cost is not None else None
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.error("Unexpected image response: %r", data)
            raise AIServiceError("Не удалось разобрать изображение из ответа AITunnel.") from exc
