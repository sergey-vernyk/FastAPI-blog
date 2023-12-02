from datetime import timedelta
from typing import Annotated, Type, Union

from fastapi import APIRouter, status, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import UJSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from accounts import schemas, models, crud
from accounts.models import User
from accounts.schemas import Token
from accounts.security import verify_password, create_access_token, get_token_data
from config import Settings
from dependencies import oauth2_scheme, DatabaseDependency, CurrentUserDependency
from posts.models import Post
from posts.schemas import UserPostsShow

router = APIRouter()
settings = Settings()
permission_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail='Only admin users be able to perform this action'
)


@router.post('/create',
             response_model=schemas.UserShow,
             status_code=status.HTTP_201_CREATED,
             summary='Create user')
async def create_user(user: schemas.UserCreate, db: DatabaseDependency) -> User:
    """
    Create user in database.
    """
    # try to get user by its email
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Email already registered')
    return crud.create_user(db=db, user=user)


@router.delete('/delete/me',
               status_code=status.HTTP_204_NO_CONTENT,
               summary='Delete own user')
async def delete_user_me(current_user: CurrentUserDependency,
                         db: DatabaseDependency) -> None:
    """
    Remove `current_user` from db.
    """
    crud.delete_user(db, current_user)


@router.delete('/delete/{user_id}',
               status_code=status.HTTP_204_NO_CONTENT,
               summary='Delete user by `user_id`')
async def delete_user_by_id(current_user: CurrentUserDependency,
                            user_id: int,
                            db: DatabaseDependency) -> None:
    """
    Remove user from db by `user_id`.
    """
    if current_user.role != 'admin':
        raise permission_exception
    db_user = crud.get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User with passed id does not exists'
        )

    crud.delete_user(db, db_user)


@router.get('/read_all',
            response_model=list[schemas.UserShow],
            status_code=status.HTTP_200_OK,
            summary='Get all users in the database')
async def read_users(token: Annotated[str, Depends(oauth2_scheme)],
                     db: DatabaseDependency,
                     skip: int = 0,
                     limit: int = 100) -> list[Type[models.User] | HTTPException]:
    """
    Obtain all users from database with `limit` and `skip`.
    """
    token_data = get_token_data(token)
    user = crud.get_user_by_username(db, token_data.username)
    if user.role != 'admin':
        raise permission_exception
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@router.get('/read/{user_id}',
            response_model=schemas.UserShow,
            status_code=status.HTTP_200_OK,
            summary='Get user by passed `user_id`')
async def read_user_by_id(current_user: CurrentUserDependency,
                          user_id: int,
                          db: DatabaseDependency) -> Type[User] | HTTPException:
    """
    Obtain user by its `user_id`.
    """
    if current_user.role != 'admin':
        raise permission_exception
    user = crud.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404, detail='User not found')
    return user


def authenticate_user(username: str,
                      password: str,
                      db: DatabaseDependency) -> Union[HTTPException, Type[User]]:
    """
    Returns user if it can be able to authenticated with passed `username` and `password`,
    raise an exception otherwise.
    """
    user = crud.get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Username or password is incorrect'
        )
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
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={'sub': user.username}, expires_delta=access_token_expires
    )

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.get('/me',
            response_model=schemas.UserShow,
            status_code=status.HTTP_200_OK,
            summary='Get info about current user')
async def read_users_me(current_user: CurrentUserDependency) -> User:
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
async def update_user_info(current_user: CurrentUserDependency,
                           data: schemas.UserUpdate,
                           db: DatabaseDependency) -> User:
    """
    Update `current_user` information from `data`.
    """
    current_user_data = jsonable_encoder(current_user)
    stored_user_model_schema = schemas.UserUpdate(**current_user_data)
    # exclude fields that wes not passed for update and considered as `None`
    data_to_update = data.model_dump(exclude_none=True)
    # update only fields which are in `data_to_update` variable
    updated_user_data = stored_user_model_schema.model_copy(update=data_to_update)
    user_data_dict = jsonable_encoder(updated_user_data)  # convert to dictionary
    return crud.update_user(db=db, user=current_user, data_to_update=user_data_dict)


@router.get('/posts',
            response_model=list[UserPostsShow],
            status_code=status.HTTP_200_OK,
            summary='Get posts that published by current user')
async def get_user_posts(db: DatabaseDependency,
                         current_user: CurrentUserDependency,
                         apply_filter: bool = False,
                         tags: str = '',
                         is_publish: bool = True,
                         rating: int = 5,
                         category: str = '') -> list[Post]:
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


@router.post('/reset_password',
             response_class=UJSONResponse,
             summary='Reset forgotten user password and set new password')
def reset_password(form: schemas.ResetUserPassword,
                   db: DatabaseDependency) -> UJSONResponse:
    """
    Reset user password, which user could forget,
    or for update old password.
    User be able to enter only its email address or its username for perform this action.
    """
    received_data = {
        'username': form.username,
        'email': form.email,
        'password': form.password,
    }
    crud.reset_user_password(db, received_data)
    return UJSONResponse(
        {'success': 'Password has been changed successfully'},
        status_code=200
    )
