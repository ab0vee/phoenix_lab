# Phoenix Lab

Одностраничный веб-сайт для AI рерайта статей с интеграцией Telegram для рассылки.

## Структура проекта

```
phoenix_lab/
├── Frontend/              # Next.js Frontend
│   ├── app/              # App Router
│   ├── public/           # Статические файлы
│   ├── package.json
│   └── next.config.js
├── Backend/              # Backend компоненты
│   ├── server.py         # Flask API сервер
│   └── requirements.txt
├── TelegramBot/          # Telegram бот
│   ├── main.py
│   ├── requirements.txt
│   └── channels.json     # Файл с каналами (создаётся автоматически)
└── README.md
```

## Компоненты

- **Frontend** (`Frontend/`) - Next.js приложение для обработки статей
- **Backend** (`Backend/server.py`) - Flask API для отправки статей в Telegram
- **Telegram бот** (`TelegramBot/main.py`) - управление каналами

## Установка

### Backend

1. Установите зависимости:
```bash
pip install -r Backend/requirements.txt
pip install -r TelegramBot/requirements.txt
```

2. Создайте файл `.env` в корне проекта:
```
BOT_TOKEN=your_bot_token_here
PORT=5000
```

### Frontend

1. Установите зависимости:
```bash
cd Frontend
npm install
# или
yarn install
```

2. Создайте файл `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:5000
```

3. Переместите логотип:
   - Переместите `Без имени-1.png` в папку `Frontend/public/`
   - Переименуйте в `logo.png`

## Запуск

1. Запустите backend сервер:
```bash
cd Backend
python server.py
```

2. Запустите Telegram бота (для управления каналами):
```bash
cd TelegramBot
python main.py
```

3. Запустите Next.js приложение:
```bash
cd Frontend
npm run dev
```

Откройте [http://localhost:3000](http://localhost:3000) в браузере.

## Использование

1. На сайте: введите URL статьи, выберите стиль рерайта
2. После обработки: нажмите кнопку "Telegram" для отправки в каналы
3. Выберите каналы и отправьте статью
4. Управление каналами: используйте Telegram бота (`/add_channel`, `/channels`)

## API Endpoints

- `GET /api/channels` - получить список каналов
- `POST /api/send-article` - отправить статью в каналы
- `GET /api/health` - проверка работоспособности
