# Capsula Bot 🎀

Telegram-бот ателье индивидуального пошива «Capsula» (Брест · Беларусь).
Свадебные / вечерние платья с примерками + корсеты с пошивом до 7 дней и доставкой по РБ.

## Что внутри

- Калькулятор пошива платьев (свадебные / вечерние) с опциями и срочностью
- Конструктор корсета: тип → ткань → закрытие → опции
- Снятие мерок (8 шагов с пояснениями)
- Галерея образов с корсетами (фото загружает админ)
- Каталог тканей (парсер `decobay.by` обновляет БД)
- Запись на примерку со слотами и подтверждением админом
- Гайды для невест, подружек, вечерних платьев, заказа корсета
- Согласие на обработку персональных данных
- Админ-панель в Telegram (заявки, примерки, слоты, загрузка фото, парсер)

## Стек

- **Python 3.11** + **aiogram 3.13**
- **Neon Postgres** + SQLAlchemy 2.0 async + Alembic
- **Upstash Redis** (FSM + rate-limit, REST API – работает в serverless)
- **Vercel Blob** (фото товаров и луков)
- **FastAPI** на webhook + деплой на **Vercel** (serverless)

---

## Установка – пошагово

### 1. Внешние сервисы (всё бесплатно для старта)

1. **Бот в Telegram** – у [@BotFather](https://t.me/BotFather) → `/newbot` → запиши токен.
   Твой ID узнай у [@userinfobot](https://t.me/userinfobot).

2. **БД Neon Postgres** – [neon.tech](https://neon.tech) → Sign in → Create Project →
   Connection string → переключи на `psycopg/asyncpg` формат:
   `postgresql+asyncpg://user:pass@host/db?ssl=require`

3. **Upstash Redis** – [upstash.com](https://upstash.com) → Console → Create Database →
   REST API → копируй `UPSTASH_REDIS_REST_URL` и `UPSTASH_REDIS_REST_TOKEN`.

4. **Vercel Blob** – после создания проекта на Vercel: Storage → Create Blob Store →
   `.env.local` или Settings → Environment Variables → `BLOB_READ_WRITE_TOKEN`.

### 2. Локальная настройка

```bash
git clone <repo>
cd capsula-bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# заполни .env своими значениями
```

### 3. Миграции БД

```bash
# создать первую миграцию (только при первом запуске)
alembic revision --autogenerate -m "init"
# применить
alembic upgrade head
```

### 4. Сидируем слоты и демо-ткани

```bash
python -m scripts.seed_slots 30          # на 30 дней вперёд
python -m scripts.seed_fabrics_demo      # демо-набор тканей
```

### 5. Локальный запуск (polling)

```bash
python -m bot.main
```

Идёшь в Telegram → пишешь боту `/start`. Должно работать.

---

## Деплой на Vercel

### 1. Подготовка

```bash
npm i -g vercel
vercel login
```

### 2. Связать проект

```bash
vercel link
```

### 3. Переменные окружения

Заходи на Vercel Dashboard → твой проект → Settings → Environment Variables.
Добавь **все** переменные из `.env` (кроме `WEBHOOK_URL` – его узнаешь после первого деплоя).

### 4. Первый деплой

```bash
vercel --prod
```

Vercel даст домен, например `https://capsula-bot.vercel.app`.
Добавь его в переменные как `WEBHOOK_URL=https://capsula-bot.vercel.app`,
снова `vercel --prod`.

### 5. Регистрируешь webhook у Telegram

Один раз открой в браузере:
```
https://capsula-bot.vercel.app/api/setup?token=<WEBHOOK_SECRET>
```

Должно вернуть `{"set": true, "url": "...", "pending_update_count": 0}`.

### 6. Миграции для production БД

Локально, с production-значением `DATABASE_URL`:
```bash
DATABASE_URL=postgresql+asyncpg://prod... alembic upgrade head
DATABASE_URL=postgresql+asyncpg://prod... python -m scripts.seed_slots 30
DATABASE_URL=postgresql+asyncpg://prod... python -m scripts.seed_fabrics_demo
```

Готово – бот в продакшене.

---

## Админ-команды

- `/admin` – открывает админ-панель (только для `ADMIN_IDS` из `.env`)

Возможности:
- 📋 Открытые заявки (просмотр, смена статусов, связь с клиентом)
- 📅 Примерки (подтверждение / отказ)
- ➕ Добавить слот (одну дату с несколькими временами через запятую)
- 📸 Загрузить фото в галерею (платье или корсет с привязкой к луку)
- 🪡 Обновить ткани (запуск парсера decobay.by)

---

## Парсер decobay.by

Запуск вручную: `python -m bot.services.decobay_parser`
Запуск из админки: 🪡 «Обновить ткани»

Cron на Vercel (раз в сутки): создай отдельный endpoint `api/cron.py` и в `vercel.json`
добавь `"crons": [{"path": "/api/cron", "schedule": "0 3 * * *"}]` (нужен Pro-план для cron).
Альтернатива – внешний планировщик (cron-job.org) который дёргает `/api/cron`.

---

## Структура проекта

```
capsula-bot/
├── api/index.py              # Vercel webhook endpoint
├── alembic/                  # миграции
├── bot/
│   ├── config.py             # настройки из .env
│   ├── factory.py            # сборка Bot + Dispatcher
│   ├── main.py               # локальный polling
│   ├── db/                   # модели SQLAlchemy
│   ├── handlers/             # хендлеры (start, calc, corset, fabrics, fitting, admin)
│   ├── keyboards/inline.py   # все inline-клавиатуры
│   ├── states/order.py       # FSM-состояния
│   ├── middlewares/          # rate-limit, логирование
│   ├── services/             # pricing, blob, redis, fsm_storage, decobay_parser
│   └── utils/                # тексты, валидаторы
├── scripts/
│   ├── seed_slots.py         # сидер слотов на N дней
│   └── seed_fabrics_demo.py  # демо-ткани
├── requirements.txt
├── vercel.json
└── .env.example
```

---

## Безопасность

- `WEBHOOK_SECRET` проверяется на каждом запросе – чужой не зайдёт через webhook
- Rate-limit 20 событий/мин/пользователь (Upstash Redis)
- Согласие на обработку ПДн обязательно перед сохранением заказа
- Все админ-хендлеры под `AdminMiddleware` – проверка `ADMIN_IDS`
- Валидация телефона РБ через `phonenumbers`, email регулярным выражением
- Санитизация всех текстовых полей перед сохранением

---

## Эстетика

Цветовая палитра для будущего сайта:
- `#F0C4CB` Blush
- `#C87D87` Antique Rose
- `#FBEAD6` Champagne
- `#6B7556` Dried Thyme
- `#E5BCA9` Bisque

Тон бота – тёплый, женственный, кофейно-винтажный. Em-dash «–».
