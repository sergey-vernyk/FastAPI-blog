from datetime import datetime, timedelta
from typing import Union

from jose import jwt
from passlib.context import CryptContext
from config import Settings
from blog.accounts.schemas import TokenData

settings = Settings()

# for hashing and verifying passwords
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check whether `plain_password` against an `hashed_password`.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Returns hash from the passed plain `password`.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """
    Returns generated jwt access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(claims=to_encode, key=settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def get_token_data(token: str) -> TokenData:
    """
    Obtain token data from passed `token` and return the data.
    """
    jwt_decode = jwt.decode(token=token,
                            key=settings.secret_key,
                            algorithms=[settings.algorithm])
    username = jwt_decode.get('sub')  # get username from `sub`
    token_data = TokenData(username=username)
    return token_data
