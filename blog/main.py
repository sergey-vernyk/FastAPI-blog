from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import Settings
from db_connection import Base, engine
from routers import posts_router, users_router

Base.metadata.create_all(bind=engine)
settings = Settings()

STATIC_DIRECTORY = ''
if settings.dev_or_prod == 'dev':
    STATIC_DIRECTORY = 'blog/static'
elif settings.dev_or_prod == 'prod':
    STATIC_DIRECTORY = '/vol/static'

DESCRIPTION = """
Blog on FastAPI Python Framework with user authentication and authorization,
blog post management, comments, search and filters, categories and tags, user's dashboard etc."""

app = FastAPI(
    swagger_ui_parameters={'persistAuthorization': True},
    title='BlogAPI',
    description=DESCRIPTION,
    version='0.1',
    root_path='/api/v1'
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
