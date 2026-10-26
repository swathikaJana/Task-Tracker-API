from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from app.cache import TaskCache
from app.config import Settings
from app.database import build_engine
from app.routes import health, tasks


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    engine = build_engine(settings.database_url)
    cache = TaskCache(settings.redis_url, settings.redis_cache_ttl_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        cache.close()
        engine.dispose()

    application = FastAPI(
        title="Task Tracker API",
        version="0.1.0",
        description="An API for creating and managing tasks.",
        lifespan=lifespan,
    )
    application.state.engine = engine
    application.state.session_factory = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    application.state.cache = cache
    application.include_router(health.router)
    application.include_router(tasks.router)
    return application


app = create_app()
