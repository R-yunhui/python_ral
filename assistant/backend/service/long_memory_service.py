import logging

logger = logging.getLogger(__name__)


class LongMemoryService:
    """mem0ai 读写封装，连接失败时降级不阻塞"""

    def __init__(self, api_key: str):
        self._available = True
        try:
            from mem0 import Memory
            self._client = Memory(api_key=api_key)
        except Exception as e:
            logger.warning(f"mem0 init failed, long memory disabled: {e}")
            self._client = None
            self._available = False

    async def add(self, user_id: str, data: dict) -> bool:
        if not self._available:
            return False
        try:
            self._client.add(data, user_id=user_id)
            return True
        except Exception as e:
            logger.warning(f"mem0 write failed for user {user_id}: {e}")
            return False

    async def search(self, user_id: str, query: str) -> list[dict]:
        if not self._available:
            return []
        try:
            return self._client.search(query, user_id=user_id)
        except Exception as e:
            logger.warning(f"mem0 search failed for user {user_id}: {e}")
            return []
