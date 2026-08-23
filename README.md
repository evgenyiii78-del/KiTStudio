# CakeHub AI Bot 3.4.2

Telegram AI-бот на **aiogram 3**. Все AI-функции работают через **AITunnel**.
Версия подготовлена для обычного Python-хостинга и **Bothost**; Railway-конфигурации в проекте нет.

## Возможности

- постоянная нижняя клавиатура;
- текстовый AI-чат с историей;
- выбор AI-агента;
- генерация изображений;
- анализ фотографий;
- SQLite;
- работа в группах по `@username`, слову «КейкХаб» или после `/bot_on`;
- `/bot_off` для отключения автоответов в группе;
- разбиение длинных AI-ответов под лимит Telegram;
- понятные сообщения об ошибках AITunnel.

## AI-агенты

- 🤖 Универсальный
- 🎂 Кондитер
- 🎨 Дизайнер
- 📣 Маркетолог
- 🛠 Технарь

## Структура

```text
.
├── main.py
├── requirements.txt
├── .env.example
├── app/
│   ├── agents.py
│   ├── config.py
│   ├── database.py
│   ├── keyboards.py
│   ├── utils.py
│   ├── handlers/
│   │   ├── common.py
│   │   ├── chat.py
│   │   └── images.py
│   └── services/
│       └── ai.py
└── data/
```

## Локальный запуск Windows

1. Установите Python 3.11–3.13.
2. Скопируйте `.env.example` в `.env`.
3. Заполните `TELEGRAM_BOT_TOKEN` и `AITUNNEL_API_KEY`.
4. Запустите `run_windows.bat`.

Или вручную:

```bat
python -m pip install -r requirements.txt
python main.py
```

## Развёртывание на Bothost

1. Загрузите проект в GitHub/GitLab или импортируйте файлы в Bothost.
2. В качестве языка выберите Python.
3. Главный файл: `main.py`.
4. Версия Python: 3.11, 3.12 или 3.13.
5. Добавьте переменные окружения из `.env.example` минимум:
   - `BOT_TOKEN` или `TELEGRAM_BOT_TOKEN`
   - `AITUNNEL_API_KEY`
6. Используйте `DATABASE_PATH=/app/data/cakehub.sqlite3` для постоянного хранения базы на Bothost.
7. После запуска проверьте лог `CakeHub AI Bot 3.4.2 started as ...`.

`requirements.txt` лежит в корне, поэтому зависимости устанавливаются платформой при сборке.

## AITunnel

По умолчанию:

```env
AITUNNEL_BASE_URL=https://api.aitunnel.ru/v1
AITUNNEL_CHAT_MODEL=auto
AITUNNEL_VISION_MODEL=auto
AITUNNEL_IMAGE_MODEL=gpt-image-2
```

Для image generation значение `AITUNNEL_IMAGE_MODEL=auto` не отправляется в AITunnel: пустое значение и `auto` принудительно нормализуются в `gpt-image-2`.
Если AITunnel вернёт 403 со списком разрешённых image-моделей, бот автоматически повторит запрос с разрешённой моделью.
После деплоя в runtime-логе ищите строку `Image model EFFECTIVE: gpt-image-2`.

## Группы

Чтобы бот видел обычные сообщения группы, в BotFather отключите Privacy Mode:

`/setprivacy` → выберите бота → `Disable`

Вызовы:

- `@username вопрос`
- `КейкХаб, вопрос`
- `/bot_on` — отвечать на все текстовые сообщения группы (только администратор)
- `/bot_off` — вернуться к ответам только по вызову (только администратор)

## Проверка проекта

```bat
python smoke_test.py
```

Ожидаемый результат:

```text
SMOKE TEST: PASS
```

## Безопасность

Не добавляйте `.env` в Git. В репозитории должен находиться только `.env.example` без настоящих токенов.
