from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from config import get_settings

settings = get_settings()

SQLALCHEMY_DATABASE_URL = settings.database_url_async
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, echo=True
)
# actual database session
SessionAsyncLocal = async_sessionmaker(expire_on_commit=False, autoflush=False, bind=engine)

# inherit from this class to create each of the database models or classes
Base = declarative_base()
