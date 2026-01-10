from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "DPA Guard API"
    environment: str = "local" # local/dev/prod

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/dpa_guard"
    
    model_config = SettingsConfigDict(
        env_prefix="DPA_",
        case_sensitive=False,
    )

settings = Settings()