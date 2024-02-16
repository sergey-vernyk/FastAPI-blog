from typing import Literal

from config import get_settings

envs = get_settings()

if envs.dev_or_prod == 'dev':
    from .development_dirs import *
elif envs.dev_or_prod == 'prod':
    from .production_dirs import *

TEMPLATES_DIR_PATH = f'{PARENT_DIR_PATH}/templates/'


def get_user_image_path(filename: str, username: str, env_type: Literal['dev', 'prod']) -> str:
    """
    Returns path where user with `username` stores its `filename` (image) and this path
    depends on current working environment, either development or production.
    """
    if env_type == 'dev':
        return f'{PARENT_DIR_PATH}/static/img/users_images/{username}/{filename}'
    elif env_type == 'prod':
        return f'/vol/static/img/users_images/{username}/{filename}'
