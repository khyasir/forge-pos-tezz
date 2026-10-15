from ...config import get_settings
from .base import FiscalAdapter, FiscalResult
from .fbr import FBRIMSAdapter
from .mock import MockFBRAdapter


def get_fiscal_adapter() -> FiscalAdapter:
    settings = get_settings()
    if settings.fiscal_provider == "fbr":
        return FBRIMSAdapter()
    return MockFBRAdapter()


__all__ = ["FiscalAdapter", "FiscalResult", "get_fiscal_adapter", "MockFBRAdapter", "FBRIMSAdapter"]
