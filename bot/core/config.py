from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    bot_token: SecretStr = Field(alias="TELEGRAM_BOT_TOKEN")
    postgres_url: SecretStr = Field(alias="POSTGRESQL_URL")
    redis_url: SecretStr = Field(alias="REDIS_URL")
    webhook_secret: SecretStr = Field(alias="WEBHOOK_SECRET")
    mandatory_join_channel: str = Field(alias="MANDATORY_JOIN_CHANNEL")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    stars_enabled: bool = Field(default=False, alias="STARS_ENABLED")

    @property
    def admin_id_set(self) -> set[int]:
        if not self.admin_ids.strip():
            return set()
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip()}


settings: Settings = Settings()  # type: ignore[call-arg]
