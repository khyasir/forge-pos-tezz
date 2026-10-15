from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ERPPushResult:
    ok: bool
    erp_ref: str = ""
    error: str = ""


class ERPAdapter(ABC):
    """Adapter interface for an ERP backend (Odoo, generic REST, or none)."""

    @abstractmethod
    def push_order(self, order: dict) -> ERPPushResult:
        ...

    def pull_products(self) -> list[dict]:
        return []

    def pull_customers(self) -> list[dict]:
        return []

    def push_refund(self, order: dict) -> ERPPushResult:
        return self.push_order(order)

    def health(self) -> bool:
        return True
