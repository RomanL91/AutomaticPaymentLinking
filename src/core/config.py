from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./db.sqlite3"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APL_",  # например APL_DATABASE_URL
        extra="ignore",
    )


settings = Settings()
