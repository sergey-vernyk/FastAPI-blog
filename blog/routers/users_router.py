from datetime import timedelta
from typing import Annotated, Type, Union

from fastapi import (
    APIRouter, status, HTTPException,
    Depends, Query, Security
)
from fastapi.responses import UJSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from accounts import schemas, models, crud
from accounts.models import User
from accounts.schemas import Token
from accounts.security import create_access_token, verify_password_or_exception
from common.utils import show_exception
from config import Settings
from dependencies import (
    DatabaseDependency,
    SecurityScopesDependency,
    get_current_user
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


@router.delete('/delete/me',
               status_code=status.HTTP_204_NO_CONTENT,
               summary='Delete own user')
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
               dependencies=[Security(get_current_user, scopes=['user:delete'])])
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
async def read_users(db: DatabaseDependency,
                     skip: int = 0,
                     limit: int = 100) -> list[Type[models.User] | HTTPException]:
    """
    Obtain all users from database with `limit` and `skip`.
    """
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@router.get('/read/{user_id}',
            response_model=schemas.UserShow,
            status_code=status.HTTP_200_OK,
            summary='Get user by passed `user_id`',
            dependencies=[Security(get_current_user, scopes=['user:read'])])
async def read_user_by_id(user_id: int,
                          db: DatabaseDependency) -> Union[HTTPException, Type[User]]:
    """
    Obtain user by its `user_id`.
    """
    user = crud.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise show_exception('user', status.HTTP_404_NOT_FOUND)
    return user


@router.post('/token',
             response_model=Token,
             status_code=status.HTTP_200_OK,
             summary='Get access token')
async def login_for_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                          db: DatabaseDependency) -> dict:
    """
    Obtain access bearer token using data from `from_data`.
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

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.get('/me',
            response_model=schemas.UserShow,
            status_code=status.HTTP_200_OK,
            summary='Get info about current user')
async def read_users_me(current_user: SecurityScopesDependency(scopes=['me:read'])) -> User:
    """
    Obtain current authenticated and active user, raise an exception otherwise.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Inactive user'
        )
    return current_user


@router.patch('/me/update',
              response_model=schemas.UserUpdate,
              status_code=status.HTTP_200_OK,
              summary='Update own user data')
async def update_user_info(current_user: SecurityScopesDependency(scopes=['me:update']),
                           data: schemas.UserUpdate,
                           db: DatabaseDependency) -> User:
    """
    Update `current_user` information from `data`.
    """
    current_user = db.merge(current_user)  # copy instance into current session `db`
    # exclude fields that were not passed for update and considered as `None`
    data_to_update = data.model_dump(exclude_none=True)
    return crud.update_user(db, current_user, data_to_update)


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
             summary='Reset forgotten user password and set new password')
async def reset_password(form: schemas.ResetUserPassword,
                         db: DatabaseDependency) -> UJSONResponse:
    """
    Reset user password, which user could forget,
    or for update old password.
    User must enter ONLY its (email or username)
    and password for perform this action.
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
