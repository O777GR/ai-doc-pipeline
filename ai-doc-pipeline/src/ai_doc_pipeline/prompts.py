"""Шаблоны промптов и утилиты санитизации."""
from __future__ import annotations

import re
from .models import DocEntity

_SYSTEM_PROMPT = """\
Ты Senior Python Architect. Генерируй лаконичную техническую документацию.
Правила:
1. Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ ЯЗЫКЕ.
2. Только факты из кода. Не выдумывай зависимости или бизнес-логику.
3. Формат: 2-3 предложения. Укажи назначение, вход/выход, сайд-эффекты.
4. Если код пустой или тривиальный → верни "Тривиальная реализация, требует ручной докстринг."
5. Не используй markdown внутри ответа. Только plain text.
"""

def sanitize_code(code: str, max_len: int) -> str:
    """Удаляет потенциальные секреты и безопасно обрезает код."""
    pattern = re.compile(r"(?i)(api[_-]?key|token|password|secret|credential)\s*[:=]\s*['\"].*?['\"]")
    cleaned = pattern.sub(r"\1: ***", code)
    return cleaned[:max_len] + ("..." if len(cleaned) > max_len else "")

def build_prompt(entity: DocEntity, snippet: str) -> str:
    """Формирует структурированный запрос для LLM."""
    return (
        f"Файл: {entity.file}\n"
        f"Сущность: {entity.kind} {entity.name}\n"
        f"Сигнатура: {entity.signature}\n"
        f"Существующий докстринг: {entity.original_doc or 'Отсутствует'}\n\n"
        f"Фрагмент кода:\n```python\n{snippet}\n```\n\n"
        "Опиши назначение и поведение. Только факты из кода. Ответ строго на русском."
    )