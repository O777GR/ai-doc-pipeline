"""Экспорт в CSV и Markdown (строго на русском)."""
from __future__ import annotations

import csv
import logging
import shutil
from collections import defaultdict
from pathlib import Path

from .models import DocEntity

logger = logging.getLogger(__name__)

_CSV_RU_MAP = {
    "file": "Файл", "name": "Имя", "kind": "Тип",
    "signature": "Сигнатура", "original_doc": "Оригинальный докстринг",
    "ai_summary": "AI-описание",
}

def export_csv(entities: list[DocEntity], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(_CSV_RU_MAP.values()))
        writer.writeheader()
        for ent in entities:
            writer.writerow({ru: getattr(ent, en) for en, ru in _CSV_RU_MAP.items()})
    logger.info("CSV сохранён: %s", out_path)

def export_markdown(entities: list[DocEntity], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[DocEntity]] = defaultdict(list)
    for ent in entities: grouped[ent.file].append(ent)

    lines = ["# 📖 Автогенерированная документация", "Сгенерировано локальным Qwen 7B + AST-парсером.\n---\n"]
    for file_path in sorted(grouped.keys()):
        lines.append(f"## 📄 `{file_path}`\n")
        for ent in grouped[file_path]:
            lines.extend([
                f"### 🔹 `{ent.name}` ({ent.kind})",
                f"- **Сигнатура:** `{ent.signature}`",
                f"- **AI-описание:** {ent.ai_summary}",
                f"- **Оригинал:** {ent.original_doc or '-'}\n",
            ])
    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Markdown сохранён: %s", out_path)

def prune_cache(cache_dir: Path, max_mb: int = 512) -> None:
    if not cache_dir.is_dir(): return
    total = sum(f.stat().st_size for f in cache_dir.glob("*.json"))
    if total <= max_mb * 1024 * 1024: return
    files = sorted(cache_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)
    for f in files:
        if total <= max_mb * 1024 * 1024: break
        total -= f.stat().st_size
        f.unlink()
    logger.info("Кэш очищен до %d МБ", total // (1024 * 1024))