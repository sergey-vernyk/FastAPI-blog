from datetime import timedelta
from typing import Annotated, Type, Union

from fastapi import (
    APIRouter, status, HTTPException,
    Depends, Query, Security, UploadFile,
    Request
)
from fastapi.responses import UJSONResponse

from accounts import schemas, crud
from accounts.models import User
from accounts.utils import create_user_image_url, create_or_update_user_folder
from common.security import (
    create_access_token,
    verify_password_or_exception,
    OAuthFormWithDefaultScopes,
    generate_csrf_token
)
from common.utils import show_exception, create_cookie
from config import Settings
from dependencies import (
    DatabaseDependency,
    SecurityScopesDependency,
    get_current_user,
    CsrfVerifyDependency
)
from posts.models import Post, Comment
from posts.schemas import UserPostsShow, UserCommentsShow

router = APIRouter()
settings = Settings()
permission_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail='Only staff users be able to perform this action'
)


@router.post('/create',
             response_model=schemas.UserShow,
             status_code=status.HTTP_201_CREATED,
             summary='Create user')
async def create_user(user: schemas.UserCreate, db: DatabaseDependency) -> Union[User, HTTPException]:
    """
    Create user in database.
    """
    # try to get user by its email
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email already registered'
        )
    return crud.create_user(db=db, user=user)


@router.post('/upload_user_image',
             response_class=UJSONResponse,
             summary='Add user\'s image',
             dependencies=[CsrfVerifyDependency])
async def create_user_photo(current_user: SecurityScopesDependency(scopes=['me:update']),
                            db: DatabaseDependency,
                            image: UploadFile) -> UJSONResponse:
    """
    Save passed `image` to provided path, and save this path to `db`.
    """
    current_user = db.merge(current_user)
    # convert image to bytes, save it by `image_save_path`,
    # save this `image_db_path` to user's `image` column in the `db`
    image_bytes = await image.read()
    image_save_path = ''
    if settings.dev_or_prod == 'dev':
        image_save_path = f'blog/static/img/users_images/{current_user.username}/{image.filename}'
    elif settings.dev_or_prod == 'prod':
        image_save_path = f'/vol/static/img/users_images/{current_user.username}/{image.filename}'
    create_or_update_user_folder(current_user)

    image_db_path = f'static/img/users_images/{current_user.username}/{image.filename}'
    with open(image_save_path, 'wb') as img:
        img.write(image_bytes)
    crud.update_user(db, current_user, {'image': image_db_path})
    return UJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'detail': f'Image `{image.filename}` has been successfully uploaded'}
    )


@router.delete('/delete/me',
               status_code=status.HTTP_204_NO_CONTENT,
               summary='Delete own user',
               dependencies=[CsrfVerifyDependency])
async def delete_user_me(current_user: SecurityScopesDependency(scopes=['me:delete']),
                         db: DatabaseDependency) -> None:
    """
    Remove `current_user` from db.
    """
    current_user = db.merge(current_user)  # copy instance into current session `db`
    crud.delete_user(db, current_user)


@router.delete('/delete/{user_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               summary='Delete user by `user_id`',
               dependencies=[Security(get_current_user, scopes=['user:delete']), CsrfVerifyDependency])
async def delete_user_by_id(user_id: int,
                            db: DatabaseDependency) -> None:
    """
    Remove user from `db` by `user_id`.
    """
    db_user = crud.get_user_by_id(db, user_id)
    if not db_user:
        raise show_exception('user', status.HTTP_404_NOT_FOUND)
    crud.delete_user(db, db_user)


@router.get('/read_all',
            response_model=list[schemas.UserShow],
            status_code=status.HTTP_200_OK,
            summary='Get all users in the database',
            dependencies=[Security(get_current_user, scopes=['user:read'])])
async def read_users(request: Request,
                     db: DatabaseDependency,
                     skip: int = 0,
                     limit: int = 100) -> list[schemas.UserShow] | HTTPException:
    """
    Obtain all users from database with `limit` and `skip`.
    """
    users = crud.get_users(db, skip=skip, limit=limit)
    return [await create_user_image_url(user, request.base_url.scheme, request.base_url.hostname) for user in users]


@router.get('/read/{user_id}',
            response_model=schemas.UserShow,
            status_code=status.HTTP_200_OK,
            summary='Get user by passed `user_id`',
            dependencies=[Security(get_current_user, scopes=['user:read'])])
async def read_user_by_id(request: Request,
                          user_id: int,
                          db: DatabaseDependency) -> Union[HTTPException, schemas.UserShow]:
    """
    Obtain user by its `user_id`.
    """
    user = crud.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise show_exception('user', status.HTTP_404_NOT_FOUND)
    return await create_user_image_url(user, request.base_url.scheme, request.base_url.hostname)


@router.post('/login_with_token',
             status_code=status.HTTP_200_OK,
             summary='Get access bearer token and login with the token')
async def login_for_token(form_data: Annotated[OAuthFormWithDefaultScopes, Depends()],
                          db: DatabaseDependency) -> UJSONResponse:
    """
    Obtain access bearer token using data from `from_data` and login in the system with the token.
    """
    user = crud.get_user_by_username(db, form_data.username)
    if not user:
        raise show_exception('user', status.HTTP_404_NOT_FOUND)
    # verify passed password from a frontend and hashed user's password in the db
    verify_password_or_exception(user.hashed_password, form_data.password)
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={'sub': user.username, 'scopes': form_data.scopes},
        expires_delta=access_token_expires
    )

    response = UJSONResponse(
        content={
            'detail': f'Access token was made on username `{form_data.username}`',
            'access_token': access_token,
            'token_type': 'bearer',
            'scopes': form_data.scopes
        },
        status_code=status.HTTP_200_OK
    )
    # generate csrf token and set it in cookies
    csrf_token = generate_csrf_token(n_bytes=64)

    create_cookie(response, key='csrftoken', value=csrf_token)

    return response


@router.get('/me',
            status_code=status.HTTP_200_OK,
            summary='Get info about current user')
async def read_users_me(request: Request,
                        current_user: SecurityScopesDependency(scopes=['me:read'])) -> schemas.UserShow:
    """
    Obtain current authenticated and active user, raise an exception otherwise.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Inactive user'
        )

    user_show = await create_user_image_url(current_user, request.base_url.scheme, request.base_url.hostname)
    return user_show


@router.patch('/me/update',
              status_code=status.HTTP_200_OK,
              summary='Update own user data',
              dependencies=[CsrfVerifyDependency])
async def update_user_info(request: Request,
                           current_user: SecurityScopesDependency(scopes=['me:update']),
                           data: schemas.UserUpdate,
                           db: DatabaseDependency) -> schemas.UserShow:
    """
    Update `current_user` information from `data`.
    """
    current_user = db.merge(current_user)  # copy instance into current session `db`
    # exclude fields that were not passed for update and considered as `None`
    data_to_update = data.model_dump(exclude_none=True)
    updated_user = crud.update_user(db, current_user, data_to_update)
    user_show = await create_user_image_url(updated_user, request.base_url.scheme, request.base_url.hostname)
    return user_show


@router.get('/me/posts',
            response_model=list[UserPostsShow],
            status_code=status.HTTP_200_OK,
            summary='Get posts that published by current user')
async def get_user_posts(db: DatabaseDependency,
                         current_user: SecurityScopesDependency(scopes=['post:read']),
                         apply_filter: Annotated[bool, Query(
                             description='Using filter with values below',
                             title='Apply filter')] = False,
                         tags: Annotated[str, Query(
                             description='Tags which can contains in posts',
                             title='Post tags',
                             examples=['tag1,tag2,tag3'])] = '',
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
            'tags': tags.split(',') if len(tags) >= 1 else [tags]
        }
    return crud.get_current_user_posts(db, current_user, criteria)


@router.get('/me/comments',
            response_model=list[UserCommentsShow],
            status_code=status.HTTP_200_OK,
            summary='Get all comments related to current user')
async def get_users_comments(db: DatabaseDependency,
                             current_user: SecurityScopesDependency(scopes=['comment:read']),
                             rate_status: Annotated[str, Query(
                                 description='Get only either liked or disliked comments')] = 'all',
                             skip: int = 0,
                             limit: int = 100) -> list[Type[Comment]]:
    """
    Obtain comments, which related to `current_user`.
    Filter comments by installed status: like or dislike.
    """
    if rate_status not in ('like', 'dislike', 'all'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Only `like`, `dislike` or `all` is allow. But <{rate_status}> was provided'
        )
    return crud.get_comments_for_user(db, current_user, rate_status, skip, limit)


@router.post('/reset_password',
             response_class=UJSONResponse,
             summary='Reset forgotten user password and set new password',
             dependencies=[CsrfVerifyDependency])
async def reset_password(form: schemas.ResetUserPassword,
                         db: DatabaseDependency) -> UJSONResponse:
    """
    Reset user password, which user could forget or for update old password.
    User must enter ONLY its (email or username) and password for perform this action.
    """
    received_data = {
        'username': form.username,
        'email': form.email,
        'password': form.password,
    }
    crud.reset_user_password(db, received_data)
    return UJSONResponse(
        content={'success': 'Password has been changed successfully'},
        status_code=status.HTTP_200_OK
    )
