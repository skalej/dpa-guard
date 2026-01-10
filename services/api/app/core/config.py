from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus

class Settings(BaseSettings):
    app_name: str = "DPA Guard API"
    environment: str = "local"

    # DB parts (no secrets in code)
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "dpa_guard"
    database_username: str = "dpa"
    database_password: str = ""  # must be provided via env/secret in non-local

    model_config = SettingsConfigDict(env_prefix="DPA_", case_sensitive=False)

    @property
    def database_url(self) -> str:
        # Encode password safely (handles special chars)
        pw = quote_plus(self.database_password) if self.database_password else ""
        return f"postgresql+psycopg://{self.database_user}:{pw}@{self.database_host}:{self.database_port}/{self.database_name}"

settings = Settings()