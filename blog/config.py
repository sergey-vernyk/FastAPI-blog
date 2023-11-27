from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Install environment variables with `.env` file.
    """
    app_name: str = 'Blog API'
    admin_email: str
    database_url: str

    model_config = SettingsConfigDict(env_file='blog/.env', env_file_encoding='utf-8')
