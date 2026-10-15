import random
from datetime import datetime

from ...config import get_settings
from .base import FiscalAdapter, FiscalResult

settings = get_settings()

_counter = {"n": 0}


class MockFBRAdapter(FiscalAdapter):
    """Deterministic-ish mock of the FBR/PRA cloud PostData response.

    Returns an invoice number shaped like the real FBR fiscal number format
    "123456-DDMMYYHHMMSS-0001" so receipts look right in demos, and can be
    told to fail a configurable fraction of the time via
    FISCAL_MOCK_FAIL_RATE to exercise the retry/offline-mode UI.
    """

    def fiscalize(self, invoice: dict) -> FiscalResult:
        if random.random() < settings.fiscal_mock_fail_rate:
            return FiscalResult(ok=False, error="FBR gateway timeout")

        _counter["n"] += 1
        now = datetime.utcnow().strftime("%d%m%y%H%M%S")
        seq = f"{_counter['n']:04d}"
        fiscal_number = f"{random.randint(100000, 999999)}-{now}-{seq}"
        qr_payload = (
            f"USIN:{invoice.get('USIN')}|INV:{fiscal_number}|AMT:{invoice.get('TotalBillAmount')}"
        )
        return FiscalResult(ok=True, fiscal_number=fiscal_number, qr_payload=qr_payload)
