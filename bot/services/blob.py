"""Vercel Blob — хранилище фото (тканей, корсетов, луков, платьев).

Когда админ присылает фото в Telegram:
1. Берём file_id → скачиваем через bot.download() в bytes
2. Загружаем в Blob через PUT /upload
3. Получаем public URL → сохраняем в БД"""

import httpx
from loguru import logger

from bot.config import settings


BLOB_API = 'https://blob.vercel-storage.com'


async def upload_to_blob(filename: str, content: bytes, content_type: str = 'image/jpeg') -> str | None:
    """Загружает файл в Vercel Blob. Возвращает public URL или None."""
    url = f'{BLOB_API}/{filename}'
    headers = {
        'authorization': f'Bearer {settings.blob_read_write_token}',
        'x-content-type': content_type,
        'x-add-random-suffix': '1',   # чтобы файлы не перезатирались
        'x-api-version': '7',
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.put(url, content=content, headers=headers)
            r.raise_for_status()
            data = r.json()
            return data.get('url')
    except Exception as e:
        logger.exception(f'Blob upload failed: {e}')
        return None


async def delete_from_blob(public_url: str) -> bool:
    """Удаляет файл из Blob по public URL."""
    headers = {
        'authorization': f'Bearer {settings.blob_read_write_token}',
        'x-api-version': '7',
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.request(
                'DELETE',
                f'{BLOB_API}/delete',
                json={'urls': [public_url]},
                headers=headers,
            )
            r.raise_for_status()
            return True
    except Exception as e:
        logger.exception(f'Blob delete failed: {e}')
        return False
