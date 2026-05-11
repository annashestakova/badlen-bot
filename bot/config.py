"""Конфигурация бота — всё через переменные окружения."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False,
    )

    # Telegram
    bot_token: str
    webhook_secret: str
    webhook_url: str | None = None
    admin_ids: list[int] = []

    # БД
    database_url: str

    # Redis (Upstash REST)
    upstash_redis_rest_url: str
    upstash_redis_rest_token: str

    # Vercel Blob
    blob_read_write_token: str

    # Бизнес
    atelier_city: str = 'Брест'
    atelier_phone: str = '+375 (29) 000-00-00'
    atelier_instagram: str = ''


settings = Settings()
