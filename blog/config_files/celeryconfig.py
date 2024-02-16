from config import get_settings
from settings import env_dirs

settings = get_settings()

# amqp settings
broker_url = env_dirs.CELERY_BROKER_URL
result_backend = env_dirs.CELERY_BACKEND_URL
broker_connection_retry_on_startup = True

# flower oauth settings
auth_provider = settings.auth_provider
auth = settings.auth
oauth2_key = settings.oauth2_key
oauth2_secret = settings.oauth2_secret
oauth2_redirect_uri = settings.oauth2_redirect_uri

task_always_eager = settings.celery_task_always_eager
