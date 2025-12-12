# Phoenix Lab Frontend (Next.js)

Frontend приложение на Next.js для Phoenix Lab.

## Установка

```bash
npm install
# или
yarn install
```

## Запуск в режиме разработки

```bash
npm run dev
# или
yarn dev
```

Откройте [http://localhost:3000](http://localhost:3000) в браузере.

## Сборка для продакшена

```bash
npm run build
npm start
```

## Переменные окружения

Создайте файл `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## Структура

- `app/` - App Router (Next.js 13+)
  - `page.tsx` - главная страница
  - `layout.tsx` - корневой layout
  - `globals.css` - глобальные стили
- `public/` - статические файлы (логотип и т.д.)

