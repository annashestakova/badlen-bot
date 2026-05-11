"""Локальный запуск через long polling – для разработки.
Использовать: python -m bot.main"""

import asyncio
import sys

from loguru import logger

from bot.factory import create_bot, create_dispatcher


async def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level='INFO', format='<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | {message}')

    bot = create_bot()
    dp = create_dispatcher()

    # снимаем webhook на всякий случай – в polling он мешает
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info('Bot started in polling mode')

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
