"""Координатор пайплайна: извлечение → генерация → экспорт."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from .models import AIConfig, DocEntity
from .prompts import _SYSTEM_PROMPT, build_prompt
from .extractor import extract_entities
from .ai_client import AIClient
from .exporter import export_csv, export_markdown, prune_cache

logger = logging.getLogger(__name__)


async def run_pipeline(root: Path, cfg: AIConfig, out_dir: Path) -> list[DocEntity]:
    """Запускает полный пайплайн генерации документации.
    
    Args:
        root: Корневая директория проекта для сканирования.
        cfg: Конфигурация пайплайна и AI-клиента.
        out_dir: Директория для сохранения результатов (CSV + MD).
        
    Returns:
        Список успешно обработанных DocEntity.
    """
    logger.info("🔍 Начало пайплайна: root=%s, out_dir=%s", root, out_dir)
    
    # Очистка старого кэша при превышении лимита
    prune_cache(cfg.cache_dir, cfg.cache_max_mb)
    
    client = AIClient(cfg)
    tasks: list[asyncio.Task[DocEntity]] = []

    # 1. Извлечение сущностей
    logger.info("📦 Извлечение сущностей из %s...", root)
    entities_raw = list(extract_entities(root, cfg.max_code_length))
    
    # 2. Применение лимита (тестовый режим)
    if cfg.max_entities is not None and len(entities_raw) > cfg.max_entities:
        logger.warning("⚠️  Ограничиваю до %d сущностей (из %d)", cfg.max_entities, len(entities_raw))
        entities_raw = entities_raw[:cfg.max_entities]
        
    logger.info("📊 Будет обработано сущностей: %d", len(entities_raw))
    
    # Если ничего не нашли — создаём пустые файлы и выходим
    if not entities_raw:
        logger.warning("⚠️  Нет задач для генерации. Создаём пустой вывод.")
        out_dir.mkdir(parents=True, exist_ok=True)
        export_csv([], out_dir / "doc_export.csv")
        export_markdown([], out_dir / "README.md")
        await client.close()
        return []

    # 3. Создание асинхронных задач
    for entity, snippet in entities_raw:
        prompt = build_prompt(entity, snippet)
        tasks.append(asyncio.create_task(_generate_and_wrap(client, prompt, entity)))

    # 4. Выполнение пула задач
    logger.info("🤖 Генерация описаний (%d задач)...", len(tasks))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 5. Фильтрация результатов
    entities: list[DocEntity] = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            logger.error("❌ Задача #%d упала: %s", i, res)
        else:
            entities.append(res)
            
    logger.info("✅ Успешно обработано: %d / %d", len(entities), len(tasks))

    # 6. Экспорт результатов
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info("💾 Экспорт в %s...", out_dir)
    export_csv(entities, out_dir / "doc_export.csv")
    export_markdown(entities, out_dir / "README.md")
    
    await client.close()
    logger.info("🏁 Пайплайн завершён.")
    return entities


async def _generate_and_wrap(client: AIClient, prompt: str, entity: DocEntity) -> DocEntity:
    """Вспомогательная функция: генерация AI-ответа + упаковка в DocEntity."""
    summary = await client.generate(_SYSTEM_PROMPT, prompt)
    return DocEntity(
        file=entity.file,
        name=entity.name,
        kind=entity.kind,
        signature=entity.signature,
        original_doc=entity.original_doc,
        ai_summary=summary,
    )