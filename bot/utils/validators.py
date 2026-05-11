"""Валидация и нормализация ввода: телефон РБ, email."""

import re
from typing import Optional

import phonenumbers
from phonenumbers import NumberParseException


PHONE_PATTERN = re.compile(r'^\+375\s?\(?\d{2}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}$')
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def normalize_phone_by(raw: str) -> Optional[str]:
    """Нормализует белорусский номер в формат +375 (XX) XXX-XX-XX.
    Возвращает None если номер невалидный."""
    if not raw:
        return None

    raw = raw.strip()
    try:
        parsed = phonenumbers.parse(raw, 'BY')
    except NumberParseException:
        return None

    if not phonenumbers.is_valid_number(parsed):
        return None

    if parsed.country_code != 375:
        return None

    national = str(parsed.national_number)
    if len(national) != 9:
        return None

    operator = national[:2]
    part1 = national[2:5]
    part2 = national[5:7]
    part3 = national[7:9]
    return f'+375 ({operator}) {part1}-{part2}-{part3}'


def validate_email(raw: str) -> Optional[str]:
    """Возвращает нормализованный email или None."""
    if not raw:
        return None
    raw = raw.strip().lower()
    if len(raw) > 128:
        return None
    if EMAIL_PATTERN.match(raw):
        return raw
    return None


def safe_float(raw: str) -> Optional[float]:
    """Безопасно парсит число (для мерок). Поддерживает 92, 92.5, 92,5."""
    if not raw:
        return None
    cleaned = raw.strip().replace(',', '.')
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if value <= 0 or value > 500:  # реалистичный диапазон в см
        return None
    return value


def sanitize_text(raw: str, max_len: int = 1000) -> str:
    """Простая санитизация: убираем управляющие символы, обрезаем длину."""
    if not raw:
        return ''
    cleaned = ''.join(c for c in raw if c.isprintable() or c in '\n\t')
    return cleaned.strip()[:max_len]
