from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./tezz.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 12

    fiscal_provider: str = "mock"  # mock | fbr
    fiscal_mock_fail_rate: float = 0.0
    fbr_sandbox_url: str = "https://esp.fbr.gov.pk:8244/FBR/v1/api/Live/PostData"
    fbr_pos_id: str = "00000"
    fbr_bearer_token: str = ""

    erp_provider: str = "mock"  # mock | odoo
    odoo_url: str = ""
    odoo_db: str = ""
    odoo_username: str = ""
    odoo_api_key: str = ""

    pos_fee_pkr: float = 1.0

    webhook_signing_timeout: int = 5

    seed_on_startup: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
