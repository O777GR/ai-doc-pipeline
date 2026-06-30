#!/usr/bin/env python3
"""Прямой запуск без проблем с импортами."""
import sys
from pathlib import Path

# Абсолютный путь к src
SRC_PATH = Path(__file__).parent / "ai-doc-pipeline" / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Теперь импортируем — пути уже настроены
from ai_doc_pipeline.cli import main

if __name__ == "__main__":
    main()