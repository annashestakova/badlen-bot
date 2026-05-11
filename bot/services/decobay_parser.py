"""Парсер каталога тканей с decobay.by.

Стратегия:
- Парсер запускается отдельно (cron или вручную из админки), НЕ на каждый запрос клиента
- Все ткани складываются в БД (Fabric.upsert по external_id)
- Бот читает только из БД – быстро и без нагрузки на партнёра

Запуск: python -m bot.services.decobay_parser
"""

import asyncio
import re
from decimal import Decimal
from typing import Iterable
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy import select

from bot.db.session import async_session_maker
from bot.db.models import Fabric, FabricCategory


BASE_URL = 'https://decobay.by'
USER_AGENT = 'Mozilla/5.0 (Capsula Atelier Bot; partner; contact via Telegram)'
REQUEST_TIMEOUT = 30.0
REQUEST_DELAY = 1.0  # пауза между запросами – уважение к серверу партнёра

# Категории на сайте → наш enum.
# Если изменится разметка сайта – правится только этот словарь.
CATEGORY_KEYWORDS = {
    FabricCategory.LACE: ['кружев', 'lace', 'гипюр'],
    FabricCategory.SATIN: ['атлас', 'satin', 'сатин'],
    FabricCategory.CHIFFON: ['шифон', 'chiffon'],
    FabricCategory.VELVET: ['бархат', 'velvet', 'велюр'],
    FabricCategory.BROCADE: ['парч', 'brocade', 'жаккард'],
    FabricCategory.SILK: ['шёлк', 'шелк', 'silk'],
}


def detect_category(text: str) -> FabricCategory:
    text_low = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_low for kw in keywords):
            return category
    return FabricCategory.OTHER


def parse_price(raw: str) -> Decimal | None:
    """Извлекает число из строки типа '12,50 BYN / м' или '24 руб./м'."""
    if not raw:
        return None
    # Берём первое число (поддерживает запятую и точку)
    m = re.search(r'(\d+(?:[.,]\d+)?)', raw.replace(' ', ''))
    if not m:
        return None
    try:
        return Decimal(m.group(1).replace(',', '.'))
    except Exception:
        return None


async def fetch(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.warning(f'fetch failed {url}: {e}')
        return None


async def discover_category_urls(client: httpx.AsyncClient) -> list[str]:
    """Ищет ссылки на категории на главной."""
    html = await fetch(client, BASE_URL)
    if not html:
        return []
    soup = BeautifulSoup(html, 'lxml')
    urls = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = (a.get_text() or '').lower()
        if any(kw in text for kws in CATEGORY_KEYWORDS.values() for kw in kws):
            urls.add(urljoin(BASE_URL, href))
        elif '/catalog/' in href or '/category/' in href:
            urls.add(urljoin(BASE_URL, href))
    return list(urls)


async def parse_product_card(card) -> dict | None:
    """Извлекает данные карточки. Селекторы могут меняться – правьте под актуальную разметку."""
    try:
        # ссылка
        link_tag = card.find('a', href=True)
        if not link_tag:
            return None
        product_url = urljoin(BASE_URL, link_tag['href'])

        # название
        name_tag = card.find(['h2', 'h3', 'h4']) or card.find(class_=re.compile('title|name'))
        name = name_tag.get_text(strip=True) if name_tag else None

        # цена
        price_tag = card.find(class_=re.compile('price'))
        price = parse_price(price_tag.get_text() if price_tag else '')

        # картинка
        img_tag = card.find('img')
        image_url = None
        if img_tag:
            src = img_tag.get('data-src') or img_tag.get('src')
            if src:
                image_url = urljoin(BASE_URL, src)

        if not name or price is None:
            return None

        # external_id из URL
        external_id = re.sub(r'[^a-z0-9]+', '-', product_url.lower())[-128:]

        return {
            'external_id': external_id,
            'name': name,
            'price': price,
            'image_url': image_url,
            'source_url': product_url,
        }
    except Exception as e:
        logger.warning(f'card parse failed: {e}')
        return None


async def parse_category(client: httpx.AsyncClient, url: str) -> list[dict]:
    html = await fetch(client, url)
    if not html:
        return []
    soup = BeautifulSoup(html, 'lxml')

    # ищем карточки – универсально
    cards = soup.find_all(class_=re.compile('product|item|card'))
    products = []
    for card in cards:
        data = await parse_product_card(card)
        if data:
            data['category'] = detect_category(data['name'])
            products.append(data)
    return products


async def upsert_fabrics(items: Iterable[dict]) -> int:
    """Вставка или обновление тканей в БД."""
    count = 0
    async with async_session_maker() as session:
        for item in items:
            ext_id = item['external_id']
            result = await session.execute(select(Fabric).where(Fabric.external_id == ext_id))
            fabric = result.scalar_one_or_none()

            if fabric:
                fabric.name = item['name']
                fabric.category = item['category']
                fabric.price_per_meter = item['price']
                fabric.image_url = item.get('image_url')
                fabric.source_url = item.get('source_url')
                fabric.is_available = True
            else:
                fabric = Fabric(
                    external_id=ext_id,
                    name=item['name'],
                    category=item['category'],
                    price_per_meter=item['price'],
                    image_url=item.get('image_url'),
                    source_url=item.get('source_url'),
                    is_available=True,
                )
                session.add(fabric)
            count += 1
        await session.commit()
    return count


async def run_parser() -> int:
    """Полный цикл парсинга. Возвращает количество обработанных тканей."""
    logger.info('Decobay parser started')
    headers = {'User-Agent': USER_AGENT, 'Accept-Language': 'ru,en'}

    async with httpx.AsyncClient(headers=headers, timeout=REQUEST_TIMEOUT) as client:
        category_urls = await discover_category_urls(client)
        logger.info(f'Found {len(category_urls)} category URLs')

        all_products: list[dict] = []
        seen_ids = set()
        for url in category_urls:
            await asyncio.sleep(REQUEST_DELAY)
            products = await parse_category(client, url)
            for p in products:
                if p['external_id'] not in seen_ids:
                    seen_ids.add(p['external_id'])
                    all_products.append(p)
            logger.info(f'{url} – {len(products)} items')

        count = await upsert_fabrics(all_products)
        logger.info(f'Saved/updated {count} fabrics')
        return count


if __name__ == '__main__':
    asyncio.run(run_parser())
