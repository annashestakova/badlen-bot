"""Создаёт слоты для примерок на ближайшие 30 дней.
Расписание по умолчанию: Пн-Сб, 10:00 / 12:00 / 14:00 / 16:00 / 18:00.

Запуск: python -m scripts.seed_slots [days]
"""

import asyncio
import sys
from datetime import date, time, timedelta

from sqlalchemy import select

from bot.db.session import async_session_maker
from bot.db.models import FittingSlot


DEFAULT_TIMES = [time(10, 0), time(12, 0), time(14, 0), time(16, 0), time(18, 0)]
DEFAULT_WEEKDAYS = {0, 1, 2, 3, 4, 5}  # Пн-Сб (Вс=6 исключаем)


async def seed(days: int = 30) -> None:
    today = date.today()
    added = 0
    skipped = 0

    async with async_session_maker() as session:
        for n in range(days):
            d = today + timedelta(days=n)
            if d.weekday() not in DEFAULT_WEEKDAYS:
                continue
            for t in DEFAULT_TIMES:
                existing = await session.execute(
                    select(FittingSlot).where(
                        FittingSlot.slot_date == d,
                        FittingSlot.slot_time == t,
                    )
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue
                session.add(FittingSlot(slot_date=d, slot_time=t, is_available=True))
                added += 1
        await session.commit()

    print(f'✅ Добавлено: {added} слотов, пропущено (уже было): {skipped}')


if __name__ == '__main__':
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    asyncio.run(seed(days))
