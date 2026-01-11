from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus

class Settings(BaseSettings):
    app_name: str = "DPA Guard API"
    environment: str = "local"

    # DB parts (no secrets in code)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "dpa_guard"
    db_user: str = "dpa"
    db_password: str = ""  # must be provided via env/secret in non-local

    model_config = SettingsConfigDict(
        env_prefix="DPA_", 
        case_sensitive=False,
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        )

    @property
    def database_url(self) -> str:
        # Encode password safely (handles special chars)
        pw = quote_plus(self.db_password)
        return f"postgresql+psycopg://{self.db_user}:{pw}@{self.db_host}:{self.db_port}/{self.db_name}"

settings = Settings()