from sqlalchemy import create_engine

from config import Settings

settings = Settings()

SQLALCHEMY_DATABASE_URL = settings.database_url_test

engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)
