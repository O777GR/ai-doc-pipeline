# 🤖 AI Doc Pipeline

Локальный генератор технической документации на базе **Qwen 7B (GGUF)** + **AST-парсер**.  
Извлекает функции и классы из Python-кода, анализирует их с помощью локальной LLM и формирует человекопонятную документацию в `README.md` + структурированную таблицу в `doc_export.csv`. Полная приватность, оптимизация под CPU, умное кэширование.

---

## 🌟 Возможности
| Функция | Описание |
|---------|----------|
| 🔒 **100% локально** | Работает без облака. Все данные остаются на вашем железе |
| 🐍 **AST-парсинг** | Точное извлечение сигнатур, докстрингов и типов |
| 🗑️ **Умная фильтрация** | Автоматически игнорирует `__pycache__`, `.venv`, тесты, миграции |
| ⚡ **Async I/O + Кэш** | `httpx` + SHA256-кэш промптов. Повторные запуски в 3-5x быстрее |
| 🛡️ **Безопасность** | Автоматическая замена секретов (`API_KEY=...`) перед отправкой в LLM |
| 📊 **Экспорт** | `README.md` (структурированный) + `doc_export.csv` (Excel-совместимый, `utf-8-sig`, русские заголовки) |

---

## 🏗️ Архитектура
```
[Python *.py] → AST Parser → Фильтрация/Санитизация → Prompt Builder
       ↓
Async HTTP Client (httpx) ↔ llama.cpp Server (localhost:8080)
       ↓
Disk Cache (SHA256) → Retry/Backoff → CSV/MD Exporter
```

---

## 🖥️ Требования
| Компонент | Минимум | Рекомендация |
|-----------|---------|--------------|
| **Python** | `3.10` | `3.11+` |
| **ОЗУ** | `16 ГБ` | `32 ГБ` (для 28K контекста + кэш) |
| **CPU** | `8 ядер` | `12+ ядер` (Xeon / Threadripper / Ryzen 9) |
| **Модель** | `Qwen 7B Q4_K_M.gguf` (~4.2 ГБ) | `Q5_K_M.gguf` при наличии RAM |
| **Бэкенд** | `llama.cpp` сервер | Собран из исходников с поддержкой AVX2/BLAS |

---

## 🚀 Установка

### 1. Подготовка окружения
```bash
cd ai-doc-pipeline
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

### 2. Запуск LLM-сервера (llama.cpp)
> ⚠️ Запустите в отдельном терминале. Опции оптимизированы под Xeon/32GB/28K контекст.
```bash
llama-server -m ./qwen-7b-Q4_K_M.gguf -c 28000 -t 12 --parallel 1 \
  --batch-size 1024 --ubatch-size 256 --cache-type-k q8_0 --cache-type-v q8_0 \
  --host 0.0.0.0 --port 8080 --no-mmap --log-disable
```
Проверка работоспособности:
```bash
curl -s http://localhost:8080/v1/models | findstr "id"  # Windows
curl -s http://localhost:8080/v1/models | grep "id"     # Linux/macOS
```

---

## 📖 Использование

### 🔹 Быстрый тест (рекомендуется для первого запуска)
Обрабатывает только 20 сущностей. Занимает ~10-15 мин.
```cmd
cd D:\Documentation
.venv\Scripts\activate
python run_docs.py "Ваш проект на python, например D:\FoodWarzPC" --base-url http://localhost:8080/v1 --limit 20 -v
```

### 🔹 Полный запуск (после проверки качества)
Без лимита, но с фильтрами и увеличенным таймаутом.
```cmd
python run_docs.py "Ваш проект на python, например D:\FoodWarzPC" --base-url http://localhost:8080/v1 --concurrency 1 --timeout 180 -v
```

### 🔹 Альтернативный запуск (через entry-point)
```cmd
ai-doc-gen "Ваш проект на python, например D:\FoodWarzPC" --base-url http://localhost:8080/v1 --timeout 180 -v
```

### 🔹 Результат
После завершения в целевой папке появится:
```
FoodWarzPC/
└── docs_output/
    ├── README.md          # Человекочитаемая документация
    └── doc_export.csv     # Таблица (открывается в Excel без кракозябр)
```

---

## ⚙️ Параметры CLI

| Флаг | По умолчанию | Описание |
|------|--------------|----------|
| `target` | *(обязательно)* | Путь к папке с Python-проектом |
| `--base-url` | `http://localhost:8080/v1` | URL OpenAI-совместимого API |
| `--model` | `qwen-7b` | Идентификатор модели в промпте |
| `--concurrency` | `2` | Параллельных запросов к LLM (1-2 для CPU) |
| `--timeout` | `90.0` | Таймаут HTTP-запроса в секундах |
| `--limit` | `None` | Макс. сущностей для теста |
| `--out-dir` | `target/docs_output` | Папка для сохранения результатов |
| `-v`, `--verbose` | `False` | Включить отладочные логи |

---

## 🔄 Интеграция с Gitea (CI/CD)

### 1. Добавьте файл `.gitea/workflows/momentum.yml`
```yaml
name: Momentum Audit & Docs Sync
on: [push, pull_request]
permissions:
  contents: write

jobs:
  audit-and-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.10", cache: "pip"}
      - name: Install deps
        run: pip install -e ".[dev]" ruff bandit
      - name: AI Docs Pipeline
        env: {AI_BASE_URL: "${{ secrets.AI_BASE_URL }}"}
        run: ai-doc-gen ./src --base-url "$AI_BASE_URL" --concurrency 1 --timeout 180
      - name: Commit generated docs
        if: github.event_name == 'pull_request'
        run: |
          git config user.name "Momentum Bot"
          git config user.email "ci@local"
          git add -A docs_output/
          git diff --cached --quiet || git commit -m "🤖 Обновить AI-документацию [skip ci]"
          git push
```

### 2. Включите Branch Protection
В настройках репозитория Gitea:
`Settings → Branches → main → Require status checks to pass → momentum-audit`

---

## 🛠️ Диагностика и FAQ

| Проблема | Решение |
|----------|---------|
| **Находит 50k+ сущностей** | Фильтры сработали не полностью. Добавьте папки в `EXCLUDE_PATH_PARTS` в `extractor.py` |
| **`TimeoutException`** | Увеличьте `--timeout 180` и снизьте `--concurrency 1`. CPU-инференс медленный |
| **`ImportError` / `NameError`** | Очистите кэш: `del /s /q __pycache__\*.pyc` и перезапустите |
| **Высокая нагрузка на RAM** | Уменьшите `-c 28000` → `-c 16000` в `llama-server` или снизьте `--concurrency` |
| **CSV открываетсья с кракозябрами** | Файл уже в `utf-8-sig`. В Excel: `Данные → Из CSV/текста → Кодировка UTF-8` |
| **Windows консоль ломает русский** | Выполните `chcp 65001` перед запуском скрипта |

---

## ✅ Production Checklist
- [ ] `llama.cpp` запущен с флагами `--parallel 1 --cache-type-k q8_0`
- [ ] В `requirements.txt` указаны только runtime-зависимости
- [ ] Тестовый запуск с `--limit 20` прошёл успешно
- [ ] Кэш `.ai_cache/` очищается при необходимости (`prune_cache` работает автоматически)
- [ ] CI/CD настроен на `pull_request`, а не на каждый `push` (экономит ресурсы)

---

## 📜 Лицензия
MIT. Используйте в коммерческих и личных проектах без ограничений.

---
💡 *Совет: для ежедневной синхронизации документации создайте `.bat`-файл в корне проекта или настройте cron-задачу. Пайплайн полностью идемпотентен.*