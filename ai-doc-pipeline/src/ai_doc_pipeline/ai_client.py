"""Async HTTP-клиент с кэшированием, ретраями и лимитом параллелизма."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path

import httpx
from .models import AIConfig

logger = logging.getLogger(__name__)

class AIClient:
    """Production-ready async LLM клиент."""
    def __init__(self, cfg: AIConfig) -> None:
        self.cfg = cfg
        self._semaphore = asyncio.Semaphore(cfg.concurrency)
        self._client = httpx.AsyncClient(
            base_url=cfg.base_url, timeout=cfg.timeout,
            limits=httpx.Limits(max_connections=cfg.concurrency * 2),
        )
        cfg.cache_dir.mkdir(parents=True, exist_ok=True)

    async def close(self) -> None:
        await self._client.aclose()

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        prompt_hash = hashlib.sha256(f"{system_prompt}|{user_prompt}".encode()).hexdigest()
        cache_path = self.cfg.cache_dir / f"{prompt_hash}.json"
        
        if cache_path.exists():
            logger.debug("Кэш: %s", cache_path.name)
            return json.loads(cache_path.read_text(encoding="utf-8"))["response"]

        async with self._semaphore:
            for attempt in range(3):
                try:
                    resp = await self._client.post(
                        "/chat/completions",
                        json={
                            "model": self.cfg.model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "max_tokens": self.cfg.max_tokens,
                            "temperature": self.cfg.temperature,
                        },
                    )
                    resp.raise_for_status()
                    text = resp.json()["choices"][0]["message"]["content"].strip()
                    
                    cache_path.write_text(
                        json.dumps({"response": text}, ensure_ascii=False), encoding="utf-8"
                    )
                    return text
                except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as exc:
                    delay = 2 ** attempt * 1.5
                    logger.warning("Запрос к ИИ упал (попытка %d): %s. Повтор через %.1fs...", attempt + 1, exc, delay)
                    await asyncio.sleep(delay)
            raise RuntimeError(f"Генерация не удалась после 3 попыток (хэш: {prompt_hash})")