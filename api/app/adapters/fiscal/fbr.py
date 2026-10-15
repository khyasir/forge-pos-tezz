import httpx

from ...config import get_settings
from .base import FiscalAdapter, FiscalResult

settings = get_settings()


class FBRIMSAdapter(FiscalAdapter):
    """Real FBR IMS cloud adapter (sandbox: esp.fbr.gov.pk:8244).

    Unused unless FISCAL_PROVIDER=fbr. Builds the exact IMS "PostData" JSON
    shape documented in docs-POS_PLAN.md section 5 and posts it with a
    bearer token. Not exercised in tests (no live sandbox credentials in
    CI) -- see adapters.fiscal.mock.MockFBRAdapter for the adapter used by
    default/tests.
    """

    def __init__(self) -> None:
        self.url = settings.fbr_sandbox_url
        self.pos_id = settings.fbr_pos_id
        self.token = settings.fbr_bearer_token

    def build_payload(self, invoice: dict) -> dict:
        return {
            "InvoiceNumber": "",
            "POSID": self.pos_id,
            "USIN": invoice["USIN"],
            "DateTime": invoice["DateTime"],
            "BuyerNTN": invoice.get("BuyerNTN", ""),
            "BuyerCNIC": invoice.get("BuyerCNIC", ""),
            "BuyerName": invoice.get("BuyerName", ""),
            "BuyerPhoneNumber": invoice.get("BuyerPhoneNumber", ""),
            "TotalBillAmount": invoice["TotalBillAmount"],
            "TotalQuantity": invoice["TotalQuantity"],
            "TotalSaleValue": invoice["TotalSaleValue"],
            "TotalTaxCharged": invoice["TotalTaxCharged"],
            "Discount": invoice.get("Discount", 0),
            "FurtherTax": invoice.get("FurtherTax", 0),
            "PaymentMode": invoice.get("PaymentMode", 1),
            "RefUSIN": invoice.get("RefUSIN", ""),
            "InvoiceType": invoice.get("InvoiceType", 1),
            "Items": invoice["Items"],
        }

    def fiscalize(self, invoice: dict) -> FiscalResult:
        payload = self.build_payload(invoice)
        try:
            resp = httpx.post(
                self.url,
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=15.0,
            )
            data = resp.json()
        except httpx.HTTPError as exc:
            return FiscalResult(ok=False, error=f"FBR request failed: {exc}")

        if str(data.get("Code")) == "100" and data.get("InvoiceNumber"):
            fiscal_number = data["InvoiceNumber"]
            qr_payload = f"USIN:{invoice['USIN']}|INV:{fiscal_number}"
            return FiscalResult(ok=True, fiscal_number=fiscal_number, qr_payload=qr_payload)
        return FiscalResult(ok=False, error=data.get("Message", "FBR rejected invoice"))

    def health(self) -> bool:
        try:
            httpx.get(self.url, timeout=5.0)
            return True
        except httpx.HTTPError:
            return False
