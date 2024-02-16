from config import get_settings

settings = get_settings()

LOGS_DIRECTORY = '/vol/logs'
STATIC_DIRECTORY = '/vol/static'
REDIS_CACHE_URL = settings.redis_cache_url_prod
CELERY_BROKER_URL = settings.celery_broker_url_prod
CELERY_BACKEND_URL = settings.celery_backend_url_prod
USER_IMAGES_DIR_PATH = '/vol/static/img/users_images/'
