"""Демо-набор тканей для запуска бота. Запускается один раз: python -m scripts.seed_fabrics_demo

После того как настроен парсер decobay.by – эти записи можно оставить (parser обновит свои по external_id),
или удалить вручную.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select

from bot.db.session import async_session_maker
from bot.db.models import Fabric, FabricCategory


DEMO_FABRICS = [
    # КРУЖЕВО
    dict(external_id='demo-lace-blush', name='Кружево «Blush»', category=FabricCategory.LACE,
         color='нежно-розовый', price_per_meter=Decimal('38.00'),
         description='Деликатное французское кружево, цветочный орнамент. Идеально для лифа корсета.'),
    dict(external_id='demo-lace-ivory', name='Кружево «Ivory dream»', category=FabricCategory.LACE,
         color='айвори', price_per_meter=Decimal('42.00'),
         description='Кружево с жемчужной нитью – свадебная классика.'),

    # АТЛАС
    dict(external_id='demo-satin-chocolate', name='Атлас «Chocolate»', category=FabricCategory.SATIN,
         color='шоколадный', price_per_meter=Decimal('24.00'),
         description='Плотный атлас с приглушённым блеском – для вечерних юбок и корсетов.'),
    dict(external_id='demo-satin-champagne', name='Атлас «Champagne»', category=FabricCategory.SATIN,
         color='шампань', price_per_meter=Decimal('24.00'),
         description='Тёплый молочно-золотистый оттенок – универсальная база.'),
    dict(external_id='demo-satin-wine', name='Атлас «Wine»', category=FabricCategory.SATIN,
         color='винный', price_per_meter=Decimal('26.00'),
         description='Глубокий бордовый – для торжественных вечерних образов.'),

    # ШИФОН
    dict(external_id='demo-chiffon-blush', name='Шифон «Blush mist»', category=FabricCategory.CHIFFON,
         color='пудровый', price_per_meter=Decimal('18.00'),
         description='Лёгкий, струящийся – для юбок и накидок.'),
    dict(external_id='demo-chiffon-cream', name='Шифон «Cream»', category=FabricCategory.CHIFFON,
         color='сливочный', price_per_meter=Decimal('18.00'),
         description='Воздушный шифон тёплого оттенка.'),

    # БАРХАТ
    dict(external_id='demo-velvet-burgundy', name='Бархат «Burgundy»', category=FabricCategory.VELVET,
         color='бордовый', price_per_meter=Decimal('45.00'),
         description='Глубокий бархат с матовым блеском – для зимних вечерних образов.'),
    dict(external_id='demo-velvet-emerald', name='Бархат «Emerald»', category=FabricCategory.VELVET,
         color='изумрудный', price_per_meter=Decimal('45.00'),
         description='Насыщенный изумруд – королевский акцент.'),

    # ПАРЧА
    dict(external_id='demo-brocade-rose', name='Парча «Antique rose»', category=FabricCategory.BROCADE,
         color='пыльно-розовый', price_per_meter=Decimal('52.00'),
         description='Парча с цветочным узором – винтажный шик.'),

    # ШЁЛК
    dict(external_id='demo-silk-pearl', name='Шёлк «Pearl»', category=FabricCategory.SILK,
         color='жемчужный', price_per_meter=Decimal('68.00'),
         description='Натуральный шёлк – мягкий, дышащий, благородный.'),
    dict(external_id='demo-silk-bisque', name='Шёлк «Bisque»', category=FabricCategory.SILK,
         color='бежевый', price_per_meter=Decimal('68.00'),
         description='Натуральный шёлк нежно-бежевого оттенка.'),
]


async def seed() -> None:
    added = 0
    skipped = 0
    async with async_session_maker() as session:
        for item in DEMO_FABRICS:
            existing = await session.execute(
                select(Fabric).where(Fabric.external_id == item['external_id'])
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue
            session.add(Fabric(**item, is_available=True))
            added += 1
        await session.commit()
    print(f'✅ Добавлено тканей: {added}, пропущено (уже было): {skipped}')


if __name__ == '__main__':
    asyncio.run(seed())
