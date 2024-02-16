from pathlib import Path

from config import get_settings

settings = get_settings()

# define parent directory path for the directory `static` (for possibility using relative path)
PARENT_DIR_PATH = str(Path(__file__).resolve().parent.parent)

LOGS_DIRECTORY = f'{PARENT_DIR_PATH}/loggers'
STATIC_DIRECTORY = f'{PARENT_DIR_PATH}/static'
REDIS_CACHE_URL = settings.redis_cache_url_dev
CELERY_BROKER_URL = settings.celery_broker_url_dev
CELERY_BACKEND_URL = settings.celery_backend_url_dev
USER_IMAGES_DIR_PATH = f'{PARENT_DIR_PATH}/static/img/users_images/'
