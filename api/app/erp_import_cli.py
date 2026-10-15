"""CLI: python -m app.erp_import_cli  (reads ODOO_* from env)."""
import json

from .database import Base, SessionLocal, engine
from . import models  # noqa: F401
from .adapters.erp.odoo_wags import OdooWagsAdapter
from .services.erp_import import run_import

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        print(json.dumps(run_import(db, OdooWagsAdapter())))
