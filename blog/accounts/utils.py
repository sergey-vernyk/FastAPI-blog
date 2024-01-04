import os
from typing import Type, Union

from fastapi.encoders import jsonable_encoder

from accounts import schemas
from accounts.models import User
from config import Settings

settings = Settings()

USER_IMAGES_DIR_PATH = ''
if settings.dev_or_prod == 'dev':
    USER_IMAGES_DIR_PATH = 'blog/static/img/users_images/'
elif settings.dev_or_prod == 'prod':
    USER_IMAGES_DIR_PATH = '/vol/static/img/users_images/'


async def create_user_image_url(current_user: Union[User, Type[User]], scheme: str, domain: str) -> schemas.UserShow:
    """
    Create and return pydantic user model `UserShow` with updated attribute `image`
    by adding to the image's url (got from db) HTTP scheme and domain,
    e.g. `http://example.com/static/img/users_images/user/user_avatar.jpg`
    instead of `/static/img/users_images/user/user_avatar.jpg`.
    """

    user_image_url = f'{scheme}://{domain}/{current_user.image}' if current_user.image else None
    user_dict = jsonable_encoder(current_user, exclude={'image'})
    user_dict.update(image=user_image_url)
    user_show = schemas.UserShow(**user_dict)
    return user_show


def create_or_update_user_folder(current_user: User) -> None:
    """
    Create user folder for user's image or remove exists image before user uploaded new image.
    """
    # if user's folder does not exists
    if not os.path.isdir(f'{USER_IMAGES_DIR_PATH}{current_user.username}'):
        os.mkdir(f'{USER_IMAGES_DIR_PATH}{current_user.username}')
    # if there is an image inside user's folder
    if os.listdir(f'{USER_IMAGES_DIR_PATH}{current_user.username}'):
        os.system(f'rm {USER_IMAGES_DIR_PATH}{current_user.username}/*')
