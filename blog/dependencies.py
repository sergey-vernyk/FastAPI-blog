from secrets import compare_digest
from typing import Annotated, Type

from fastapi import Depends, HTTPException, Security, Cookie, Header, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from accounts import models, crud
from accounts.schemas import TokenData
from config import Settings
from db_connection import SessionLocal

settings = Settings()
# for authentication using Bearer Token obtained with a password
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl='/users/login_with_token',
    scopes={
        'post:create': 'Write a new post',
        'category:create': 'Create a new category for posts',
        'post:read': 'Read a post\'s information',
        'post:update': 'Update a post\'s information',
        'post:delete': 'Delete a post',

        'comment:update': 'Update a comment\'s body',
        'comment:delete': 'Delete a comment',
        'comment:create': 'Create a comment',
        'comment:rate': 'Set like or dislike for a comment',
        'comment:read': 'Read a comment',

        'user:read': 'Read a user\'s information',
        'user:update': 'Update a user\'s information',
        'user:delete': 'Delete a user',

        'me:delete': 'Delete own user',
        'me:update': 'Update own user info',
        'me:read': 'Read own profile information',
    }
)


def get_db():
    """
    Dependency will create a new SQLAlchemy `SessionLocal`
    that will be used in a single request, and then close it once the request is finished.
    """
    with SessionLocal() as db:
        yield db


DatabaseDependency = Annotated[Session, Depends(get_db)]


async def get_current_user(security_scopes: SecurityScopes,
                           token: Annotated[str, Depends(oauth2_scheme)],
                           db: DatabaseDependency) -> models.User:
    """
    Obtain current user by passed `token`. Used as dependency.
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = 'Bearer'

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': authenticate_value},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get('sub')
        if username is None:
            raise credentials_exception
        token_scopes = payload.get('scopes', [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except (JWTError, ValidationError):
        raise credentials_exception
    user = crud.get_user_by_username(db=db, username=token_data.username)
    if user is None:
        raise credentials_exception
    # try to compare security scopes from decoded user's access bearer token with scopes for current endpoint
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Not enough permissions',
                headers={'WWW-Authenticate': authenticate_value},
            )
    return user


CurrentUserDependency = Annotated[models.User, Depends(get_current_user)]


def SecurityScopesDependency(scopes: list) -> Type[models.User]:
    """
    Return user with security metadata dependency taking in account passed `scopes`.
    """
    return Annotated[models.User, Security(get_current_user, scopes=scopes)]


def verify_csrf_token(cookie_token: str = Cookie(None,
                                                 include_in_schema=False,
                                                 alias='csrftoken'),
                      header_token: str = Header(None,
                                                 convert_underscores=False,
                                                 include_in_schema=False,
                                                 alias='X-CSRFToken')) -> None:
    """
    Compare CSRF tokens from request header while client making request,
    and from cookies on client side. Raise an exception if tokens are not equals.
    """
    csrf_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail='CSRF token missing or incorrect'
    )

    if not all([header_token, cookie_token]):
        raise csrf_exception

    from_header_bytes = str.encode(header_token, encoding='utf-8')
    from_cookie_bytes = str.encode(cookie_token, encoding='utf-8')
    are_tokens_equals = compare_digest(from_header_bytes, from_cookie_bytes)

    if not are_tokens_equals:
        raise csrf_exception


CsrfVerifyDependency = Depends(verify_csrf_token)
