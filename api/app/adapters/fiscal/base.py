from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class FiscalResult:
    ok: bool
    fiscal_number: str = ""
    qr_payload: str = ""
    error: str = ""


class FiscalAdapter(ABC):
    """Adapter interface for a tax-authority fiscalization backend (FBR IMS, PRA, SRB)."""

    @abstractmethod
    def fiscalize(self, invoice: dict) -> FiscalResult:
        ...

    def health(self) -> bool:
        return True
