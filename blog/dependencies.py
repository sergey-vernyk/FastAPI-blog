from db_connection import SessionLocal


def get_db():
    """
    Dependency will create a new SQLAlchemy `SessionLocal`
    that will be used in a single request, and then close it once the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        # make sure the database session is always closed after the request
        db.close()
