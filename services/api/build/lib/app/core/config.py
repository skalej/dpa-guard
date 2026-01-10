from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "DPA Guard API"
    environment: str = "local"

    model_config = SettingsConfigDict(
        env_prefix="DPA_",
        case_sensitive=False,
    )

settings = Settings()