from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Install environment variables with `.env` file.
    """
    app_name: str = 'Blog API'
    admin_email: str
    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    database_url_test: str
    dev_or_prod: str

    model_config = SettingsConfigDict(env_file='blog/.env', env_file_encoding='utf-8')
