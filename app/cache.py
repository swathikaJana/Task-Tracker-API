import json
import logging
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)
TASK_CACHE_PREFIX = "task-tracker:tasks:"


class TaskCache:
    """Best-effort Redis cache; database operations remain authoritative."""

    def __init__(self, redis_url: str | None, ttl_seconds: int) -> None:
        self._client = (
            Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
                health_check_interval=30,
            )
            if redis_url
            else None
        )
        self._ttl_seconds = ttl_seconds

    def get(self, key: str) -> Any | None:
        if self._client is None:
            return None
        try:
            value = self._client.get(key)
            return json.loads(value) if value is not None else None
        except (RedisError, ValueError) as error:
            logger.warning("Redis cache read failed: %s", error)
            return None

    def set(self, key: str, value: Any) -> None:
        if self._client is None:
            return
        try:
            self._client.setex(key, self._ttl_seconds, json.dumps(value))
        except (RedisError, TypeError, ValueError) as error:
            logger.warning("Redis cache write failed: %s", error)

    def clear_tasks(self) -> None:
        if self._client is None:
            return
        try:
            keys = list(self._client.scan_iter(match=f"{TASK_CACHE_PREFIX}*", count=100))
            if keys:
                self._client.delete(*keys)
        except RedisError as error:
            logger.warning("Redis task cache invalidation failed: %s", error)

    def ping(self) -> bool:
        if self._client is None:
            return False
        try:
            return bool(self._client.ping())
        except RedisError as error:
            logger.warning("Redis health check failed: %s", error)
            return False

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
