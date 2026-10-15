import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SEED_ON_STARTUP"] = "false"
os.environ["FISCAL_MOCK_FAIL_RATE"] = "0.0"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  (register models on Base.metadata)
from app.database import Base, get_db
from app.main import app
from app.security import generate_api_key, hash_pin

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seeded(db_session):
    """Minimal hand-built tenant (company/branch/terminal/user/tax/payment
    methods/one product) -- deliberately NOT the demo seed script, so these
    tests stay fast and independent of its random order generation.
    """
    company = models.Company(id="co1", name="Test Co", ntn="123", strn="456", tax_authority="PRA")
    branch = models.Branch(id="br1", company_id="co1", name="Main")
    terminal = models.Terminal(id="t1", branch_id="br1", name="T1")
    owner = models.User(id="u1", company_id="co1", name="Owner", role="owner", pin_hash=hash_pin("1111"))
    api_key = models.ApiKey(id="k1", company_id="co1", key=generate_api_key())
    tax = models.Tax(id="tax1", company_id="co1", name="Standard", cash_rate=0.16, card_rate=0.05, is_default=True)
    cash_pm = models.PaymentMethod(id="pm_cash", company_id="co1", name="Cash", code="cash", fiscal_payment_mode=1)
    card_pm = models.PaymentMethod(id="pm_card", company_id="co1", name="Card", code="card", fiscal_payment_mode=2)
    category = models.Category(id="cat1", company_id="co1", name="Food")
    product = models.Product(id="p1", company_id="co1", category_id="cat1", tax_id="tax1", name="Burger", price=500)
    db_session.add_all([company, branch, terminal, owner, api_key, tax, cash_pm, card_pm, category, product])
    db_session.commit()
    return {
        "company_id": "co1",
        "branch_id": "br1",
        "terminal_id": "t1",
        "api_key": api_key.key,
        "product_id": "p1",
        "cash_pm": "pm_cash",
        "card_pm": "pm_card",
    }


def auth_headers(seeded):
    return {"Authorization": f"Bearer {seeded['api_key']}"}
