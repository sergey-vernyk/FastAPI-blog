from fastapi import FastAPI

from accounts import models
from db_connection import engine
from routers import users

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(router=users.router)
