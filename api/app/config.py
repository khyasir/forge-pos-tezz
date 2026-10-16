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
    default_tax_authority: str = "PRA"  # Punjab Revenue Authority by default (FBR | PRA | SRB)
    fbr_sandbox_url: str = "https://esp.fbr.gov.pk:8244/FBR/v1/api/Live/PostData"
    fbr_pos_id: str = "00000"
    fbr_bearer_token: str = ""

    erp_provider: str = "mock"  # mock | odoo
    odoo_url: str = ""
    odoo_db: str = ""
    odoo_username: str = ""
    odoo_api_key: str = ""
    odoo_password: str = ""  # alternative to api key; load from untracked env file only
    odoo_branch_id: int = 24  # branch.wags "Test" on staging
    odoo_import_limit: int = 500
    odoo_customer_limit: int = 200
    odoo_order_note_prefix: str = "TEZZ-TEST"
    odoo_delivery_product_id: int = 0  # optional Odoo product used for the delivery-charge line
    odoo_import_images: bool = True

    retry_worker_enabled: bool = True
    retry_worker_interval_s: int = 15

    pos_fee_pkr: float = 1.0

    webhook_signing_timeout: int = 5

    seed_on_startup: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
