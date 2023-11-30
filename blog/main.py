from fastapi import FastAPI

from accounts import models
from db_connection import engine
from blog.routers import posts_router
from blog.routers import users_router


models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(router=users_router.router, tags=['users'])
app.include_router(router=posts_router.router, tags=['posts'])
