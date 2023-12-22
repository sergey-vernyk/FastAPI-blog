import secrets
from datetime import datetime, timedelta
from typing import Union, Annotated

from fastapi import HTTPException, status
from fastapi.param_functions import Form
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext

from accounts.schemas import TokenData
from config import Settings

DEFAULT_ACCESS_SCOPES = 'me:read me:update me:delete post:read post:delete post:create comment:read'

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
    username = jwt_decode.get('sub')
    scopes = jwt_decode.get('scopes')
    token_data = TokenData(username=username, scopes=scopes)
    return token_data


def verify_password_or_exception(hashed_password: str, plain_password: str) -> None:
    """
    Returns None if passwords verification is successfully,
    and raise an exception otherwise.
    """
    if not verify_password(plain_password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect password',
            headers={'WWW-Authenticate': 'Bearer'}
        )


class OAuthFormWithDefaultScopes(OAuth2PasswordRequestForm):
    """
    Override constructor of `OAuth2PasswordRequestForm`
    in order to add several access scopes by default.
    """

    def __init__(self,
                 *,
                 username: Annotated[str, Form()],
                 password: Annotated[str, Form()],
                 grant_type: Annotated[Union[str, None], Form(pattern="password")] = None,
                 scope: Annotated[str, Form()] = DEFAULT_ACCESS_SCOPES,
                 client_id: Annotated[Union[str, None], Form()] = None,
                 client_secret: Annotated[Union[str, None], Form()] = None) -> None:
        super().__init__(
            username=username, password=password,
            grant_type=grant_type, scope=scope,
            client_id=client_id, client_secret=client_secret
        )


def generate_csrf_token(n_bytes: Union[int, None] = None) -> str:
    """
    Returns CSRF token which consists from `n_bytes` random bytes,
    or returns reasonable default CSRF token if `n_bytes` is None.
    """
    return secrets.token_urlsafe(n_bytes)
