# 🤖 AI Doc Pipeline

Локальный генератор технической документации на базе Qwen 7B (GGUF) + AST-парсер. 
Экспорт в `CSV` и `README.md`. Интегрируется с Gitea Actions для аудита кода.

## 🚀 Быстрый старт
```bash
# 1. Создаём окружение
python -m venv .venv && source .venv/bin/activate

# 2. Устанавливаем зависимости
pip install -r requirements.txt

# 3. Устанавливаем проект в режиме разработки (для команды ai-doc-gen)
pip install -e .

# 4. Запуск
ai-doc-gen ./src