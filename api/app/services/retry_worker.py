"""Background thread: automatic retry (with backoff) of failed FBR/PRA and
Odoo pushes, so cashiers no longer need to press Retry."""
import logging
import threading

from ..config import get_settings

log = logging.getLogger("tezz.retry")
_stop = threading.Event()
_thread: threading.Thread | None = None


def _loop():
    from ..database import SessionLocal
    from .orders import retry_due_orders

    interval = get_settings().retry_worker_interval_s
    while not _stop.wait(interval):
        db = SessionLocal()
        try:
            stats = retry_due_orders(db)
            if stats["fiscal"] or stats["erp"]:
                log.info("auto-retry: %s", stats)
        except Exception as exc:  # noqa: BLE001
            log.warning("auto-retry error: %s", type(exc).__name__)
            db.rollback()
        finally:
            db.close()


def start():
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="tezz-retry", daemon=True)
    _thread.start()


def stop():
    _stop.set()
