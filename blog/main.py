from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from db_connection import Base, engine
from routers import posts_router, users_router

Base.metadata.create_all(bind=engine)

description = """
Blog on FastAPI Python Framework with user authentication and authorization,
blog post management, comments, search and filters, categories and tags, user's dashboard etc."""

app = FastAPI(swagger_ui_parameters={
    'persistAuthorization': True
},
    title='BlogAPI',
    description=description,
    version='0.1')
app.include_router(router=users_router.router, prefix='/users', tags=['users'])
app.include_router(router=posts_router.router, prefix='/posts', tags=['posts'])

# mount directory for static files
app.mount('/static', StaticFiles(directory='blog/static'), name='static')
