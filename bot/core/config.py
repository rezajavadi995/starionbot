from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    bot_token: SecretStr = Field(alias="TELEGRAM_BOT_TOKEN")
    postgres_url: SecretStr = Field(alias="POSTGRESQL_URL")
    redis_url: SecretStr = Field(alias="REDIS_URL")
    webhook_secret: SecretStr = Field(alias="WEBHOOK_SECRET")


settings = Settings()
