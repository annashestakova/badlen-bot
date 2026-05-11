"""Middlewares: rate limit, логирование, обработка ошибок."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from loguru import logger

from bot.services.redis_client import rate_limit_check
from bot.utils.texts import RATE_LIMIT_EXCEEDED, ERROR_GENERIC


class RateLimitMiddleware(BaseMiddleware):
    """20 событий в минуту на пользователя."""

    def __init__(self, limit: int = 20, window: int = 60):
        self.limit = limit
        self.window = window

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user = event.from_user

        if not user:
            return await handler(event, data)

        try:
            allowed = await rate_limit_check(user.id, self.limit, self.window)
        except Exception as e:
            logger.warning(f'Rate limit check failed: {e}')
            return await handler(event, data)

        if not allowed:
            if isinstance(event, Message):
                await event.answer(RATE_LIMIT_EXCEEDED)
            elif isinstance(event, CallbackQuery):
                await event.answer(RATE_LIMIT_EXCEEDED, show_alert=True)
            return None

        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    """Логирование + перехват исключений."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            text_preview = (event.text or '<no text>')[:80]
            logger.info(f'[msg {event.from_user.id} @{event.from_user.username}] {text_preview!r}')
        elif isinstance(event, CallbackQuery) and event.from_user:
            logger.info(f'[cb  {event.from_user.id} @{event.from_user.username}] {event.data!r}')

        try:
            return await handler(event, data)
        except Exception as e:
            logger.exception(f'Handler error: {e}')
            try:
                if isinstance(event, Message):
                    await event.answer(ERROR_GENERIC)
                elif isinstance(event, CallbackQuery):
                    await event.answer(ERROR_GENERIC, show_alert=True)
            except Exception:
                pass
            return None
