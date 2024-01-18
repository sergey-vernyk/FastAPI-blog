from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Install environment variables with `.env` file.
    """

    app_name: str = 'Blog API'
    admin_email: str
    database_url: str
    database_url_test: str
    # access JWT token data
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    dev_or_prod: str  # environment type
    # email send
    email_password: str
    email_host: str
    email_from: str
    email_port: int
    api_version: int
    # token generator data
    secret_key_token_generator: str
    token_expired_timeout: int
    # redis for celery
    celery_broker_url_dev: str | None
    celery_broker_url_prod: str | None
    celery_backend_url_dev: str | None
    celery_backend_url_prod: str | None
    celery_task_always_eager: bool = False
    # flower oauth settings
    auth_provider: str
    auth: str
    oauth2_key: str
    oauth2_secret: str
    oauth2_redirect_uri: str

    model_config = SettingsConfigDict(env_file='blog/.env', env_file_encoding='utf-8')


@lru_cache
def get_settings() -> Settings:
    """
    Returns settings which creates only once.
    """
    return Settings()
