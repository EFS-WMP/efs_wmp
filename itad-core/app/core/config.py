import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.getenv("ITAD_CORE_DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/itad_core")
    port: int = int(os.getenv("ITAD_CORE_PORT", "8001"))
    site: str = os.getenv("ITAD_CORE_SITE", "MAIN")
    blind_receiving: bool = os.getenv("ITAD_CORE_BLIND_RECEIVING", "false").lower() == "true"


settings = Settings()
