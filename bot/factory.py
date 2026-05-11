"""Фабрика бота и диспетчера – используется и для polling, и для webhook."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.handlers import (
    start, guides, dress_calc, corset_constructor, corset_looks,
    measurements, contacts, fitting, fabrics, admin,
)
from bot.middlewares.common import RateLimitMiddleware, LoggingMiddleware
from bot.services.fsm_storage import UpstashStorage


def create_bot() -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    storage = UpstashStorage()
    dp = Dispatcher(storage=storage)

    # middlewares
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())

    # routers (порядок важен – admin последним, чтобы команды бота работали для всех)
    dp.include_router(start.router)
    dp.include_router(guides.router)
    dp.include_router(dress_calc.router)
    dp.include_router(corset_constructor.router)
    dp.include_router(corset_looks.router)
    dp.include_router(measurements.router)
    dp.include_router(contacts.router)
    dp.include_router(fitting.router)
    dp.include_router(fabrics.router)
    dp.include_router(admin.router)

    return dp
