import logging
from base64 import urlsafe_b64encode, urlsafe_b64decode
from typing import Annotated

from fastapi import (
    APIRouter, status, HTTPException,
    Query, Security, UploadFile,
    Request
)
from fastapi.responses import UJSONResponse
from fastapi_cache.decorator import cache

from accounts import schemas, crud, tasks
from accounts.models import User
from accounts.utils import (
    create_user_image_url,
    create_or_update_user_folder,
    verify_uid_and_token_from_url,
    token_generator
)
from common.crud_operations import CrudManagerAsync
from common.security import (
    get_password_hash
)
from common.utils import show_exception, PickleCoderRedis
from dependencies import (
    DatabaseDependency,
    ProjSettingsDependency,
    SecurityScopesDependency,
    get_current_user,
    CsrfVerifyDependency
)
from loggers.logs_config import (
    set_endpoint_logger,
    FORMATTER_FORMAT,
    FORMATTER_DATA_FORMAT,
)
from posts.models import Post, Comment
from posts.schemas import UserPostsShow, UserCommentsShow
from settings import env_dirs

router = APIRouter()
permission_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail='Only staff users be able to perform this action'
)

endpoints_logger = logging.getLogger(__name__)
endpoints_formatter = logging.Formatter(fmt=FORMATTER_FORMAT, datefmt=FORMATTER_DATA_FORMAT)
endpoint_handler = logging.FileHandler(filename=f'{env_dirs.LOGS_DIRECTORY}/users_endpoints.log', encoding='utf-8')
endpoint_handler.setFormatter(endpoints_formatter)
endpoints_logger.addHandler(endpoint_handler)


@router.post('/create',
             response_model=schemas.UserShow,
             status_code=status.HTTP_201_CREATED,
             summary='Create User',
             operation_id='create-user',
             responses={400: {'detail': 'Email or username is already exists'}})
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/create')
async def create_user(request: Request,
                      user: schemas.UserCreate,
                      db: DatabaseDependency,
                      settings: ProjSettingsDependency) -> User | HTTPException:
    """
    Create user in database.
    """
    crud_manager = CrudManagerAsync(db, User)
    # try to get user by its email or its username
    db_user = await crud_manager.retrieve(User.email == user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email already registered'
        )
    db_user = await crud_manager.retrieve(User.username == user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User with provided username already registered'
        )

    created_user = await crud_manager.create(
        instance_data=user.model_dump(exclude={'password'}),
        set_password=True,
        password=user.password
    )
    # compose context for email with account activation link
    email_context = {
        'protocol': request.base_url.scheme,
        'domain': request.base_url.hostname,
        'username': created_user.username,
        'email': created_user.email,
        'uid': urlsafe_b64encode(created_user.username.encode('utf-8')).decode('utf-8'),
        'token': token_generator.make_token(created_user),
        'api_version': settings.api_version,
        'subject': 'Account activation'
    }

    # send email to user's email with link for activate account
    tasks.send_email_to_user.delay(
        context=email_context,
        html_template_location='email/account_activation_email.html',
        plain_text_template_location='email/account_activation_email.txt',
        send_to=created_user.email
    )

    return created_user


@router.get('/activate_account/{uidb64}/{token}',
            status_code=status.HTTP_200_OK,
            include_in_schema=False,
            operation_id='activate-user-account',
            summary='Activate User\'s Account After Registration')
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/activate_account/{uidb64}/{token}')
async def activate_user_account(db: DatabaseDependency, uidb64: str, token: str) -> UJSONResponse:
    """
    Activate user's account after following link in user's email after successfully registration.
    Activation link contains with username encoded in `uidb64` and generated disposable `token`.
    Function will check `uidb64` and `token` and if they will be correcter
    than will make user's `is_active` parameter as True.
    """
    user = await verify_uid_and_token_from_url(db, uidb64, token)
    if user is not None:
        # activate user account
        await CrudManagerAsync(db, User).partial_update(user, {'is_active': True})
        return UJSONResponse(
            content={'detail': f'Account of `{user.username}` has been activated!'},
            status_code=status.HTTP_200_OK
        )
    return UJSONResponse(
        content={'detail': 'Activation link is invalid!'},
        status_code=status.HTTP_200_OK
    )


@router.post('/upload_user_image',
             response_class=UJSONResponse,
             summary='Add User\'s Image',
             dependencies=[CsrfVerifyDependency],
             operation_id='upload-user-image',
             responses={401: {'detail': 'Not enough permissions'}})
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/upload_user_image')
async def create_user_photo(current_user: SecurityScopesDependency(scopes=['me:update']),
                            db: DatabaseDependency,
                            image: UploadFile,
                            settings: ProjSettingsDependency) -> UJSONResponse:
    """
    Save passed `image` to provided path, and save this path to `db`.
    """
    current_user = await db.merge(current_user)
    # convert image to bytes, save it by `image_save_path`
    image_bytes = await image.read()
    create_or_update_user_folder(current_user)
    # save `image_db_path` to user's `image` column in the `db`
    image_db_path = f'static/img/users_images/{current_user.username}/{image.filename}'
    image_save_path = env_dirs.get_user_image_path(image.filename, current_user.username, settings.dev_or_prod)

    with open(image_save_path, 'wb') as img:
        img.write(image_bytes)

    await CrudManagerAsync(db, User).partial_update(current_user, {'image': image_db_path})
    return UJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'detail': f'Image `{image.filename}` has been successfully uploaded'}
    )


@router.delete('/delete/me',
               status_code=status.HTTP_204_NO_CONTENT,
               summary='Delete Own Account',
               dependencies=[CsrfVerifyDependency],
               operation_id='delete-current-authenticated-user',
               responses={401: {'detail': 'Not enough permissions'}})
async def delete_user_me(current_user: SecurityScopesDependency(scopes=['me:delete']),
                         db: DatabaseDependency) -> None:
    """
    Remove `current_user` from db.
    """
    current_user = await db.merge(current_user)  # copy instance into current session `db`
    await CrudManagerAsync(db, User).destroy(current_user)


@router.delete('/delete/{user_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               summary='Delete User By `user_id`',
               operation_id='delete-user-by-id',
               dependencies=[Security(get_current_user, scopes=['user:delete']), CsrfVerifyDependency],
               responses={
                   401: {'detail': 'Not enough permissions'},
                   404: {'detail': 'User is not found'}}
               )
async def delete_user_by_id(user_id: int, db: DatabaseDependency) -> None:
    """
    Remove user from `db` by `user_id`.
    """
    crud_manager = CrudManagerAsync(db, User)
    db_user = await crud_manager.retrieve(User.id == user_id)
    if not db_user:
        raise show_exception('user', status.HTTP_404_NOT_FOUND)

    await crud_manager.destroy(db_user)


@router.get('/read_all',
            response_model=list[schemas.UserShow],
            status_code=status.HTTP_200_OK,
            summary='Get All Users',
            operation_id='get-all-users',
            dependencies=[Security(get_current_user, scopes=['user:read'])],
            responses={401: {'detail': 'Not enough permissions'}})
@cache(expire=300, namespace=User.__tablename__)
async def read_users(request: Request,
                     db: DatabaseDependency,
                     skip: int = 0,
                     limit: int = 100) -> list[schemas.UserShow] | HTTPException:
    """
    Obtain all users from database with `limit` and `skip`.
    """
    users = await CrudManagerAsync(db, User).retrieve(skip=skip, limit=limit, many=True)
    return [await create_user_image_url(user, request.base_url.scheme, request.base_url.hostname) for user in users]


@router.get('/read/{user_id}',
            response_model=schemas.UserShow,
            status_code=status.HTTP_200_OK,
            summary='Get User By Passed `user_id`',
            operation_id='get-user-by-id',
            dependencies=[Security(get_current_user, scopes=['user:read'])],
            responses={
                401: {'detail': 'Not enough permissions'},
                404: {'detail': 'User is not found'}}
            )
@cache(expire=300, namespace=User.__tablename__)
async def read_user_by_id(request: Request,
                          user_id: int,
                          db: DatabaseDependency) -> HTTPException | schemas.UserShow:
    """
    Obtain user by its `user_id`.
    """
    user = await CrudManagerAsync(db, User).retrieve(User.id == user_id)
    if user is None:
        raise show_exception('user', status.HTTP_404_NOT_FOUND)

    return await create_user_image_url(user, request.base_url.scheme, request.base_url.hostname)


@router.get('/me',
            status_code=status.HTTP_200_OK,
            summary='Get Info About Current User',
            operation_id='get-current-user-info',
            responses={401: {'detail': 'Not enough permissions'}})
@cache(expire=300, namespace=User.__tablename__)
async def read_users_me(request: Request,
                        current_user: SecurityScopesDependency(scopes=['me:read'])) -> schemas.UserShow:
    """
    Obtain current authenticated and user.
    """
    return await create_user_image_url(current_user, request.base_url.scheme, request.base_url.hostname)


@router.patch('/me/update',
              status_code=status.HTTP_200_OK,
              summary='Update Own User Data',
              operation_id='update-current-user-info',
              dependencies=[CsrfVerifyDependency],
              responses={
                  401: {'detail': 'Not enough permissions'},
                  403: {'detail': 'CSRF token missing or incorrect'}}
              )
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/me/update')
async def update_user_info(request: Request,
                           current_user: SecurityScopesDependency(scopes=['me:update']),
                           update_data: schemas.UserUpdate,
                           db: DatabaseDependency) -> schemas.UserShow:
    """
    Update `current_user` information from `data`.
    """
    current_user = await db.merge(current_user)  # copy instance into current session `db`
    # exclude fields that were not passed for update and considered as `None`
    data_to_update = update_data.model_dump(exclude_none=True)
    updated_user = await CrudManagerAsync(db, User).partial_update(current_user, data_to_update)
    user_show = await create_user_image_url(updated_user, request.base_url.scheme, request.base_url.hostname)
    return user_show


@router.get('/me/posts',
            response_model=list[UserPostsShow],
            status_code=status.HTTP_200_OK,
            operation_id='get-current-user-posts',
            summary='Get Posts That Published By Current User',
            responses={401: {'detail': 'Not enough permissions'}})
@cache(expire=300, namespace=User.__tablename__)
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/me/posts')
async def get_user_posts(db: DatabaseDependency,
                         current_user: SecurityScopesDependency(scopes=['post:read']),
                         apply_filter: Annotated[bool, Query(
                             description='Using filter with values below',
                             title='Apply filter')] = False,
                         tags: Annotated[list, Query(
                             description='Tags which can contains in posts',
                             title='Post tags')] = None,
                         is_publish: Annotated[bool, Query(
                             description='Whether posts were publish or not')] = True,
                         rating: Annotated[int, Query(
                             description='Rating of posts. Greater or equal',
                             ge=0, le=5)] = 5,
                         category: Annotated[str, Query(
                             description="Post's category")] = '') -> list[Post]:
    """
    Obtain all posts behalf `current_user` with `criteria`.
    If not passed `criteria`, filtering performed only by `current_user`.
    """
    if not apply_filter:
        criteria = None
    else:
        criteria = {
            'is_publish': is_publish,
            'rating': rating,
            'category': category,
            'tags': [tag.lower() for tag in tags] if tags else []
        }

    return await crud.get_current_user_posts(db, current_user, criteria)


@router.get('/me/comments',
            response_model=list[UserCommentsShow],
            status_code=status.HTTP_200_OK,
            operation_id='get-current-user-comments',
            summary='Get All Comments Related To Current User',
            responses={
                401: {'detail': 'Not enough permissions'},
                400: {'detail': 'Wrong criteria was provided (neither like, dislike nor all)'}}
            )
# used custom `PickleCoderRedis` coder in order to avoid `maximum recursion exceeded` error,
# while FastAPI tries to save response data to Redis Cache.
@cache(expire=300, namespace=User.__tablename__, coder=PickleCoderRedis)
async def get_users_comments(db: DatabaseDependency,
                             current_user: SecurityScopesDependency(scopes=['comment:read']),
                             rate_status: Annotated[str, Query(
                                 description='Get only either liked or disliked comments')] = 'all',
                             skip: int = 0,
                             limit: int = 100) -> list[Comment]:
    """
    Obtain comments, which related to `current_user`.
    Filter comments by installed status: like or dislike.
    """
    if rate_status not in ('like', 'dislike', 'all'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Only `like`, `dislike` or `all` is allow. But <{rate_status}> was provided'
        )
    return await crud.get_comments_for_user(db, current_user, rate_status, skip, limit)


@router.post('/reset_password',
             operation_id='reset-account-password',
             summary='Reset Forgotten User Password and Set New One',
             responses={
                 400: {'detail': 'Not provided required data for action'},
                 404: {'detail': 'User is not found'}}
             )
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/reset_password')
async def reset_password(request: Request,
                         reset_pswd_form: schemas.ResetUserPassword,
                         db: DatabaseDependency,
                         settings: ProjSettingsDependency) -> UJSONResponse:
    """
    Reset user password, which user could forget or for update old password.
    User must enter ONLY its (email or username) and password for perform this action.
    """
    crud_manager = CrudManagerAsync(db, User)
    if reset_pswd_form.username:
        db_user = await crud_manager.retrieve(User.username == reset_pswd_form.username)
    elif reset_pswd_form.email:
        db_user = await crud_manager.retrieve(User.email == reset_pswd_form.email)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='You must provide either username or email for reset password'
        )
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Username `{reset_pswd_form.username}` does not exists'
        )
    # encrypt and encode new password and encode username
    # format is `hashed_password:username`
    uid_pass = (f'{urlsafe_b64encode(get_password_hash(reset_pswd_form.password).encode("utf-8")).decode("utf-8")}:'
                f'{urlsafe_b64encode(db_user.username.encode("utf-8")).decode("utf-8")}')
    email_context = {
        'protocol': request.base_url.scheme,
        'domain': request.base_url.hostname,
        'username': db_user.username,
        'email': db_user.email,
        'uid_pass': uid_pass,
        'token': token_generator.make_token(db_user),
        'api_version': settings.api_version,
        'subject': 'Password reset confirmation'
    }
    # send email to user's email with link for confirm reset password
    tasks.send_email_to_user.delay(
        context=email_context,
        html_template_location='email/password_reset_confirm_email.html',
        plain_text_template_location='email/password_reset_confirm_email.txt',
        send_to=db_user.email
    )

    return UJSONResponse(
        content={'detail': 'Check your email! '
                           'You have to receive email with instruction for reset password'},
        status_code=status.HTTP_200_OK
    )


@router.get('/confirm_reset_password/{uid_pass}/{token}',
            include_in_schema=False,
            operation_id='confirm-reset-password',
            status_code=status.HTTP_200_OK,
            summary='Confirm Password Reset')
@set_endpoint_logger(level='info', module_name=__name__, endpoint_path='/confirm_reset_password/{uid_pass}/{token}')
async def confirm_reset_password(db: DatabaseDependency, uid_pass: str, token: str) -> UJSONResponse:
    """
    Confirm reset password by verifying received `uidb64` with encoded username and disposable `token`.
    If this parameters will turn to be out correct, then user password reset request will be confirmed.
    """
    # get encoded new hashed password and encoded username
    passwd_b64, username_b64 = uid_pass.split(':')
    user = await verify_uid_and_token_from_url(db, username_b64, token)
    if user is not None:
        data = {'password': urlsafe_b64decode(passwd_b64).decode('utf-8')}
        await CrudManagerAsync(db, User).partial_update(user, update_password=True, data_to_update=data)
        return UJSONResponse(
            content={'detail': 'Password has been changed successfully'},
            status_code=status.HTTP_200_OK
        )
    return UJSONResponse(
        content={'detail': 'Activation link is invalid!'},
        status_code=status.HTTP_200_OK
    )
