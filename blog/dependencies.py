from typing import Annotated, Type

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from accounts import models
from accounts.schemas import TokenData
from config import Settings
from db_connection import SessionLocal

settings = Settings()
# for authentication using Bearer Token obtained with a password
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')


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


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                           db: Session = Depends(get_db)) -> Type[models.User]:
    """
    Obtain current user by passed `token`. Used as dependency.
    """

    from routers.users import read_user_by_username

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get('sub')
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = read_user_by_username(username=token_data.username, db=db)
    if user is None:
        raise credentials_exception
    return user
