from datetime import timedelta, datetime
from typing import Annotated

from fastapi import Depends, APIRouter, status
from fastapi.responses import UJSONResponse

from accounts.models import User
from common.crud_operations import CrudManagerAsync
from common.security import (
    OAuthFormWithDefaultScopes,
    verify_password_or_exception,
    create_access_token,
    generate_csrf_token
)
from common.utils import show_exception, create_cookie, delete_cookie
from dependencies import DatabaseDependency, ProjSettingsDependency, SecurityScopesDependency
from loggers.logs_config import set_endpoint_logger

router = APIRouter()


@router.post('/login_with_token',
             status_code=status.HTTP_200_OK,
             operation_id='get-access-token-and-login-user',
             summary='Get Access Bearer Token And Login With The Token',
             responses={404: {'detail': 'User is not found'}})
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/login_with_token')
async def login_for_token(login_data: Annotated[OAuthFormWithDefaultScopes, Depends()],
                          db: DatabaseDependency,
                          settings: ProjSettingsDependency) -> UJSONResponse:
    """
    Obtain access bearer token using data from `from_data` and login in the system with the token.
    """
    crud_manager = CrudManagerAsync(db, User)
    user = await crud_manager.retrieve(User.username == login_data.username)
    if user is None:
        raise show_exception('user', status.HTTP_404_NOT_FOUND)
    # verify passed password from a frontend and hashed user's password in the db
    verify_password_or_exception(user.hashed_password, login_data.password)
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={'sub': user.username, 'scopes': login_data.scopes},
        expires_delta=access_token_expires
    )

    response = UJSONResponse(
        content={
            'access_token': access_token,
            'token_type': 'bearer',
            'scopes': login_data.scopes,
            'expires': settings.access_token_expire_minutes
        },
        status_code=status.HTTP_200_OK
    )

    await crud_manager.partial_update(user, {'last_login': datetime.utcnow()})
    # generate csrf token and set it in cookies
    csrf_token = generate_csrf_token(n_bytes=64)
    create_cookie(response, key='csrftoken', value=csrf_token)

    return response


@router.get('/logout',
            status_code=status.HTTP_200_OK,
            operation_id='logout-user',
            summary='Log Out User',
            responses={401: {'detail': 'Not enough permissions'}})
async def logout(current_user: SecurityScopesDependency(scopes=['me:read'])) -> UJSONResponse:
    """
    Log out user from system and delete cookies from its client.
    """
    response = UJSONResponse(
        content={'detail': f'You ({current_user.username}) successfully logged out from the system'},
        status_code=status.HTTP_200_OK
    )

    delete_cookie(response, 'csrftoken')

    return response
