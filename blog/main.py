from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from accounts import router as accounts_router
from accounts.auth import router as auth_router
from common.utils import endpoint_cache_key_builder
from config import get_settings
from db_connection import Base, engine
from posts import router as posts_router
from settings import env_dirs

settings = get_settings()


async def create_db_tables():
    """
    Creates tables in a database.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Initialize cache for endpoints and create tables in a database (if they does not exists)
    when application starting.

    """
    redis = aioredis.from_url(env_dirs.REDIS_CACHE_URL)
    FastAPICache.init(RedisBackend(redis), prefix='fastapi-cache', key_builder=endpoint_cache_key_builder)
    await create_db_tables()
    yield


DESCRIPTION = """Blog on FastAPI Python Framework with user authentication and authorization,
blog post management, comments, search and filters, categories and tags, user's dashboard etc."""

app = FastAPI(
    lifespan=lifespan,
    swagger_ui_parameters={'persistAuthorization': True},
    title='BlogAPI',
    description=DESCRIPTION,
    version='0.1',
    root_path=f'/api/v{settings.api_version}'
)
app.include_router(router=accounts_router.router, prefix='/users', tags=['Users'])
app.include_router(router=posts_router.router, prefix='/posts', tags=['Posts'])
app.include_router(router=auth_router.router, prefix='/auth', tags=['Auth'])

# mount directory for static files
app.mount('/static', StaticFiles(directory=env_dirs.STATIC_DIRECTORY), name='static')
app.add_middleware(
    CORSMiddleware,
    allow_origins='http://localhost:5174',
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
