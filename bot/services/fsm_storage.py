"""Aiogram FSM storage поверх Upstash Redis REST API.

Стандартный RedisStorage из aiogram требует TCP-соединение, что не работает
на serverless (Vercel). Этот класс — адаптер: тот же интерфейс, под капотом REST."""

import json
from typing import Any, Optional

from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType

from bot.services.redis_client import redis


class UpstashStorage(BaseStorage):
    """FSM storage поверх Upstash Redis REST."""

    def __init__(self, prefix: str = 'fsm', ttl: int = 60 * 60 * 24 * 7):
        self.prefix = prefix
        self.ttl = ttl  # 7 дней — больше чем нужно для долгих диалогов

    def _state_key(self, key: StorageKey) -> str:
        return f'{self.prefix}:state:{key.bot_id}:{key.chat_id}:{key.user_id}'

    def _data_key(self, key: StorageKey) -> str:
        return f'{self.prefix}:data:{key.bot_id}:{key.chat_id}:{key.user_id}'

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        rkey = self._state_key(key)
        if state is None:
            await redis.delete(rkey)
        else:
            value = state.state if hasattr(state, 'state') else str(state)
            await redis.set(rkey, value, ex=self.ttl)

    async def get_state(self, key: StorageKey) -> Optional[str]:
        rkey = self._state_key(key)
        value = await redis.get(rkey)
        return value

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        rkey = self._data_key(key)
        if not data:
            await redis.delete(rkey)
        else:
            await redis.set(rkey, json.dumps(data, default=str), ex=self.ttl)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        rkey = self._data_key(key)
        value = await redis.get(rkey)
        if not value:
            return {}
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}

    async def close(self) -> None:
        pass
