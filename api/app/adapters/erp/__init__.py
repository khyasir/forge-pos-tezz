from ...config import get_settings
from .base import ERPAdapter, ERPPushResult
from .mock import MockERPAdapter
from .odoo import OdooAdapter


def get_erp_adapter() -> ERPAdapter:
    settings = get_settings()
    if settings.erp_provider == "odoo":
        return OdooAdapter()
    return MockERPAdapter()


__all__ = ["ERPAdapter", "ERPPushResult", "get_erp_adapter", "MockERPAdapter", "OdooAdapter"]
