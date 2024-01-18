from config import get_settings

settings = get_settings()

CELERY_BROKER_URL = ''
if settings.dev_or_prod == 'dev':
    CELERY_BROKER_URL = settings.celery_broker_url_dev
elif settings.dev_or_prod == 'prod':
    CELERY_BROKER_URL = settings.celery_broker_url_prod

CELERY_BACKEND_URL = ''
if settings.dev_or_prod == 'dev':
    CELERY_BACKEND_URL = settings.celery_backend_url_dev
elif settings.dev_or_prod == 'prod':
    CELERY_BACKEND_URL = settings.celery_backend_url_prod

broker_url = CELERY_BROKER_URL
result_backend = CELERY_BACKEND_URL
broker_connection_retry_on_startup = True
task_always_eager = settings.celery_task_always_eager
# flower oauth settings
auth_provider = settings.auth_provider
auth = settings.auth
oauth2_key = settings.oauth2_key
oauth2_secret = settings.oauth2_secret
oauth2_redirect_uri = settings.oauth2_redirect_uri
