"""Модели конфигурации и сущностей кода."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class AIConfig:
    """Конфигурация пайплайна, оптимизированная под CPU/32GB RAM."""
    base_url: str = "http://localhost:8080/v1"
    model: str = "qwen-7b"
    max_tokens: int = 1200
    temperature: float = 0.2
    timeout: float = 90.0
    concurrency: int = 2
    max_code_length: int = 3000
    cache_dir: Path = Path(".ai_cache")
    cache_max_mb: int = 512
    max_entities: int | None = None  # ✅ Лимит сущностей (None = без лимита)

@dataclass(frozen=True, slots=True)
class DocEntity:
    """Представляет извлечённую сущность кода с AI-описанием."""
    file: str
    name: str
    kind: str
    signature: str
    original_doc: str
    ai_summary: str = ""