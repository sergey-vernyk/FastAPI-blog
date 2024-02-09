from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from config import Settings

settings = Settings()

# database URL for SQLAlchemy
SQLALCHEMY_DATABASE_URL = settings.database_url
# SQLAlchemy `engine`
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, echo=True
)
# this instance will be the actual database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# we will inherit from this class to create each of the database models or classes
Base = declarative_base()
