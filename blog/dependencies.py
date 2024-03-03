from secrets import compare_digest
from typing import Annotated, Type

from fastapi import Depends, HTTPException, Security, Cookie, Header, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from accounts import models
from accounts.auth.schemas import TokenData
from common.crud_operations import CrudManagerAsync
from config import Settings, get_settings
from db_connection import SessionAsyncLocal

settings = get_settings()
# for authentication using Bearer Token obtained with a password
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f'/api/v{settings.api_version}/users/login_with_token',
    scheme_name='JWT',
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


async def get_db():
    """
    Creates a new SQLAlchemy AsyncSession instance
    that will be used in a single request.
    """
    async with SessionAsyncLocal() as db:
        yield db


DatabaseDependency = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(security_scopes: SecurityScopes,
                           token: Annotated[str, Depends(oauth2_scheme)],
                           db: DatabaseDependency) -> models.User:
    """
    Obtain current user by passed `token`.
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
    user = await CrudManagerAsync(db, models.User).retrieve(models.User.username == token_data.username)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Inactive user. Activate your account in order to do this action'
        )
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
    Compare CSRF tokens from request header and from cookies on client side,
    while client making request. Raise an exception if tokens are not equals.
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

# project settings
ProjSettingsDependency = Annotated[Settings, Depends(get_settings)]
