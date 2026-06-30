"""CLI-интерфейс для запуска пайплайна."""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .models import AIConfig
from .orchestrator import run_pipeline

__version__ = "0.2.0"  # Hardcoded fallback — работает всегда


def setup_logging(verbose: bool = False) -> None:
    """Настраивает логирование."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
        encoding="utf-8",
    )


def main() -> None:
    """Точка входа CLI."""
    parser = argparse.ArgumentParser(
        prog="ai-doc-gen",
        description="Генератор технической документации на базе локального ИИ.",
    )
    
    # Обязательные аргументы
    parser.add_argument(
        "target",
        type=Path,
        help="Корневая директория для сканирования Python-файлов",
    )
    
    # Опции подключения к ИИ
    parser.add_argument(
        "--base-url",
        default="http://localhost:8080/v1",
        help="Базовый URL API llama.cpp (по умолчанию: http://localhost:8080/v1)",
    )
    parser.add_argument(
        "--model",
        default="qwen-7b",
        help="Идентификатор модели (по умолчанию: qwen-7b)",
    )
    
    # Опции производительности
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Макс. параллельных запросов к ИИ (по умолчанию: 2)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
        help="Таймаут HTTP-запроса в секундах (по умолчанию: 90.0)",
    )
    
    # Опции вывода и отладки
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Макс. сущностей для обработки (тестовый режим, по умолчанию: без лимита)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Директория для сохранения результатов (по умолчанию: target/docs_output)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Включить отладочные логи",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Показать версию и выйти",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Валидация входных данных
    if not args.target.is_dir():
        print(f"❌ Ошибка: Директория не найдена: {args.target}", file=sys.stderr)
        sys.exit(1)

    # Сборка конфигурации
    cfg = AIConfig(
        base_url=args.base_url.rstrip("/"),
        model=args.model,
        concurrency=args.concurrency,
        timeout=args.timeout,
        max_entities=args.limit,
    )
    
    out_dir = args.out_dir or args.target / "docs_output"

    # Запуск пайплайна
    try:
        asyncio.run(run_pipeline(args.target, cfg, out_dir))
        print(f"✅ Документация сохранена: {out_dir}")
    except KeyboardInterrupt:
        print("\n⛔ Прервано пользователем.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        logging.getLogger(__name__).critical("Критическая ошибка: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()