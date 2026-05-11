"""Webhook endpoint для Vercel.

Vercel-функция: входной файл должен экспортировать ASGI-приложение `app`.
Telegram POST → /api/webhook → FastAPI → aiogram Dispatcher.

Безопасность:
- проверяем header X-Telegram-Bot-Api-Secret-Token (Telegram отправляет его при setWebhook)
- если не совпадает с WEBHOOK_SECRET – игнорируем

При первой подаче на Vercel нужно один раз вызвать setWebhook:
  GET /api/setup?token=<WEBHOOK_SECRET>
"""

import json

from fastapi import FastAPI, Request, HTTPException
from aiogram.types import Update

from bot.config import settings
from bot.factory import create_bot, create_dispatcher


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# Bot и Dispatcher переиспользуются между запросами в рамках одного контейнера Vercel
_bot = create_bot()
_dp = create_dispatcher()


@app.post('/api/webhook')
async def telegram_webhook(request: Request):
    # 1) проверка секретного токена
    incoming_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if incoming_secret != settings.webhook_secret:
        raise HTTPException(status_code=403, detail='Forbidden')

    # 2) парсим апдейт
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail='Bad JSON')

    update = Update.model_validate(data, context={'bot': _bot})

    # 3) скармливаем диспетчеру
    await _dp.feed_update(_bot, update)

    return {'ok': True}


@app.get('/api/setup')
async def setup_webhook(token: str):
    """Одноразовая регистрация webhook у Telegram.
    Вызвать после деплоя: https://<домен>/api/setup?token=<WEBHOOK_SECRET>"""
    if token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail='Forbidden')
    if not settings.webhook_url:
        raise HTTPException(status_code=400, detail='WEBHOOK_URL не задан в окружении')

    url = f'{settings.webhook_url.rstrip("/")}/api/webhook'
    result = await _bot.set_webhook(
        url=url,
        secret_token=settings.webhook_secret,
        drop_pending_updates=True,
        allowed_updates=['message', 'callback_query'],
    )
    info = await _bot.get_webhook_info()
    return {
        'set': result,
        'url': info.url,
        'pending_update_count': info.pending_update_count,
        'last_error_message': info.last_error_message,
    }


@app.get('/api/health')
async def health():
    return {'status': 'ok'}
