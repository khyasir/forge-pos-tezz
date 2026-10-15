import uuid

from .base import ERPAdapter, ERPPushResult


class MockERPAdapter(ERPAdapter):
    """Always-succeeds ERP adapter used by default/tests."""

    def push_order(self, order: dict) -> ERPPushResult:
        return ERPPushResult(ok=True, erp_ref=f"MOCKERP-{uuid.uuid4().hex[:8]}")
