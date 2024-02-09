import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_cache import FastAPICache
from fastapi_cache.backends.memcached import MemcachedBackend
from pymemcache.client import base

from config import get_settings
from db_connection import Base, engine
from routers import posts_router, users_router

Base.metadata.create_all(bind=engine)
settings = get_settings()
memcache_client = base.Client(server='localhost')


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Initialize cache for endpoints when application starts.
    """
    FastAPICache.init(MemcachedBackend(mcache=memcache_client), prefix='fast_api_cache')
    yield


# define parent directory path for the directory `static` (for possibility using relative path)
parent_dir_path = os.path.dirname(os.path.realpath(__file__))

STATIC_DIRECTORY = ''
if settings.dev_or_prod == 'dev':
    STATIC_DIRECTORY = f'{parent_dir_path}/static'
elif settings.dev_or_prod == 'prod':
    STATIC_DIRECTORY = '/vol/static'

DESCRIPTION = """
Blog on FastAPI Python Framework with user authentication and authorization,
blog post management, comments, search and filters, categories and tags, user's dashboard etc."""

app = FastAPI(
    lifespan=lifespan,
    swagger_ui_parameters={'persistAuthorization': True},
    title='BlogAPI',
    description=DESCRIPTION,
    version='0.1',
    root_path=f'/api/v{settings.api_version}'
)
app.include_router(router=users_router.router, prefix='/users', tags=['users'])
app.include_router(router=posts_router.router, prefix='/posts', tags=['posts'])

# mount directory for static files
app.mount('/static', StaticFiles(directory=STATIC_DIRECTORY), name='static')
app.add_middleware(
    CORSMiddleware,
    allow_origins='http://localhost:5174',
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
