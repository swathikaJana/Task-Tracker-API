import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str | None
    redis_cache_ttl_seconds: int

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg://task_tracker:task_tracker@localhost:5432/task_tracker",
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0") or None,
            redis_cache_ttl_seconds=int(os.getenv("REDIS_CACHE_TTL_SECONDS", "30")),
        )
