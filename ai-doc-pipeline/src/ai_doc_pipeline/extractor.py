"""AST-парсинг и извлечение сущностей кода с фильтрацией мусора."""
from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Iterator

from docstring_parser import parse as parse_doc
from .models import DocEntity
from .prompts import sanitize_code

logger = logging.getLogger(__name__)

# Папки и паттерны, которые нужно игнорировать
EXCLUDE_DIRS = {
    '__pycache__', '.venv', 'venv', 'env', '.eggs', 'site-packages',
    'dist', 'build', '.git', '.tox', 'node_modules', '.pytest_cache',
    '.mypy_cache', '.ruff_cache', 'egg-info', 'eggs', 'wheels',
}

EXCLUDE_PATH_PARTS = {
    'tests', 'test', 'specs', 'docs', 'migrations', 'alembic',
    'static', 'media', 'templates', 'locale', 'fixtures',
}


def _should_skip(py_file: Path, root: Path) -> bool:
    """Проверяет, нужно ли пропустить файл по путям и имени."""
    # Пропускаем файлы, начинающиеся с _ (кроме __init__.py)
    if py_file.name.startswith("_") and py_file.name != "__init__.py":
        return True
    
    # Получаем относительный путь и проверяем части
    try:
        rel_parts = py_file.relative_to(root).parts
    except ValueError:
        return True  # Файл не в root, пропускаем
    
    # Проверяем каждую часть пути на наличие в исключениях
    for part in rel_parts:
        if part in EXCLUDE_DIRS or part in EXCLUDE_PATH_PARTS:
            return True
        # Пропускаем скрытые папки (.folder)
        if part.startswith(".") and part not in (".", ".."):
            return True
    
    return False


def extract_entities(root: Path, max_code_len: int = 3000) -> Iterator[tuple[DocEntity, str]]:
    """Рекурсивно обходит *.py и возвращает (сущность, фрагмент).
    
    Args:
        root: Корневая директория для сканирования.
        max_code_len: Макс. длина фрагмента кода для отправки в LLM.
        
    Yields:
        Tuple[DocEntity, sanitized_code_snippet]
    """
    scanned = 0
    skipped = 0
    
    for py_file in root.rglob("*.py"):
        if not py_file.is_file():
            continue
            
        if _should_skip(py_file, root):
            skipped += 1
            continue
            
        scanned += 1

        try:
            source = py_file.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            logger.warning("Пропущен файл %s: %s", py_file, exc)
            continue
        except PermissionError:
            logger.warning("Нет прав на чтение %s", py_file)
            continue

        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError as exc:
            logger.warning("Ошибка парсинга %s: %s", py_file, exc)
            continue

        lines = source.splitlines()
        for node in ast.walk(tree):
            match node:
                case ast.FunctionDef(name=name, lineno=ln) | ast.AsyncFunctionDef(name=name, lineno=ln):
                    if _is_private(name): 
                        continue
                    doc = ast.get_docstring(node)
                    if doc:
                        parsed = parse_doc(doc)
                        doc = parsed.short_description or doc
                    sig = _format_signature(node)
                    snippet = sanitize_code("\n".join(lines[ln-1 : ln+20]), max_code_len)
                    yield DocEntity(
                        file=str(py_file.relative_to(root)), name=name, kind="function",
                        signature=f"def {name}{sig}", original_doc=doc or "",
                    ), snippet

                case ast.ClassDef(name=name, lineno=ln):
                    if _is_private(name): 
                        continue
                    doc = ast.get_docstring(node)
                    snippet = sanitize_code("\n".join(lines[ln-1 : ln+10]), max_code_len)
                    yield DocEntity(
                        file=str(py_file.relative_to(root)), name=name, kind="class",
                        signature="(self, ...)", original_doc=doc or "",
                    ), snippet
    
    logger.info("📁 Просканировано файлов: %d, пропущено (фильтры): %d", scanned, skipped)


def _format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Форматирует сигнатуру функции в человекочитаемый вид."""
    args = [arg.arg for arg in node.args.args]
    if node.args.vararg: 
        args.append(f"*{node.args.vararg.arg}")
    if node.args.kwarg: 
        args.append(f"**{node.args.kwarg.arg}")
    ret = ast.unparse(node.returns) if node.returns else ""
    return f"({', '.join(args)}){f' -> {ret}' if ret else ''}"


def _is_private(name: str) -> bool:
    """Проверяет, является ли имя приватным (начинается с _ но не __)."""
    return name.startswith("_") and not name.startswith("__")