import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models, schemas
from .config import get_settings
from .crud_router import make_crud_router
from .database import Base, SessionLocal, engine
from .routers import api_keys, auth, demo, erp, fiscal, orders, shifts, sync, users
from .seed import run_seed

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(
    title="Tezz POS API",
    description=(
        "Fast, FBR/PRA-ready POS API for Pakistani restaurants and shops. "
        "Offline-first cashier, fiscal + ERP adapters, webhooks, and a generic "
        "CRUD surface for the full back-office data model."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            run_seed(db)
        finally:
            db.close()


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(api_keys.router)
app.include_router(orders.router)
app.include_router(sync.router)
app.include_router(fiscal.router)
app.include_router(erp.router)
app.include_router(shifts.router)
app.include_router(demo.router)

app.include_router(
    make_crud_router(
        model=models.Company,
        create_schema=schemas.CompanyCreate,
        update_schema=schemas.CompanyUpdate,
        read_schema=schemas.CompanyRead,
        prefix="/api/v1/companies",
        tags=["companies"],
        company_scoped=False,
    )
)
app.include_router(
    make_crud_router(
        model=models.Branch,
        create_schema=schemas.BranchCreate,
        update_schema=schemas.BranchUpdate,
        read_schema=schemas.BranchRead,
        prefix="/api/v1/branches",
        tags=["branches"],
    )
)
app.include_router(
    make_crud_router(
        model=models.Terminal,
        create_schema=schemas.TerminalCreate,
        update_schema=schemas.TerminalUpdate,
        read_schema=schemas.TerminalRead,
        prefix="/api/v1/terminals",
        tags=["terminals"],
        company_scoped=False,
    )
)
app.include_router(
    make_crud_router(
        model=models.Category,
        create_schema=schemas.CategoryCreate,
        update_schema=schemas.CategoryUpdate,
        read_schema=schemas.CategoryRead,
        prefix="/api/v1/categories",
        tags=["categories"],
    )
)
app.include_router(
    make_crud_router(
        model=models.Tax,
        create_schema=schemas.TaxCreate,
        update_schema=schemas.TaxUpdate,
        read_schema=schemas.TaxRead,
        prefix="/api/v1/taxes",
        tags=["taxes"],
    )
)
app.include_router(
    make_crud_router(
        model=models.KitchenStation,
        create_schema=schemas.KitchenStationCreate,
        update_schema=schemas.KitchenStationUpdate,
        read_schema=schemas.KitchenStationRead,
        prefix="/api/v1/kitchen-stations",
        tags=["kitchen-stations"],
    )
)
app.include_router(
    make_crud_router(
        model=models.Product,
        create_schema=schemas.ProductCreate,
        update_schema=schemas.ProductUpdate,
        read_schema=schemas.ProductRead,
        prefix="/api/v1/products",
        tags=["products"],
    )
)
app.include_router(
    make_crud_router(
        model=models.ModifierGroup,
        create_schema=schemas.ModifierGroupCreate,
        update_schema=schemas.ModifierGroupUpdate,
        read_schema=schemas.ModifierGroupRead,
        prefix="/api/v1/modifier-groups",
        tags=["modifier-groups"],
    )
)
app.include_router(
    make_crud_router(
        model=models.Modifier,
        create_schema=schemas.ModifierCreate,
        update_schema=schemas.ModifierUpdate,
        read_schema=schemas.ModifierRead,
        prefix="/api/v1/modifiers",
        tags=["modifiers"],
        company_scoped=False,
    )
)
app.include_router(
    make_crud_router(
        model=models.Deal,
        create_schema=schemas.DealCreate,
        update_schema=schemas.DealUpdate,
        read_schema=schemas.DealRead,
        prefix="/api/v1/deals",
        tags=["deals"],
    )
)
app.include_router(
    make_crud_router(
        model=models.Customer,
        create_schema=schemas.CustomerCreate,
        update_schema=schemas.CustomerUpdate,
        read_schema=schemas.CustomerRead,
        prefix="/api/v1/customers",
        tags=["customers"],
    )
)
app.include_router(
    make_crud_router(
        model=models.Floor,
        create_schema=schemas.FloorCreate,
        update_schema=schemas.FloorUpdate,
        read_schema=schemas.FloorRead,
        prefix="/api/v1/floors",
        tags=["floors"],
        company_scoped=False,
    )
)
app.include_router(
    make_crud_router(
        model=models.Table,
        create_schema=schemas.TableCreate,
        update_schema=schemas.TableUpdate,
        read_schema=schemas.TableRead,
        prefix="/api/v1/tables",
        tags=["tables"],
        company_scoped=False,
    )
)
app.include_router(
    make_crud_router(
        model=models.PaymentMethod,
        create_schema=schemas.PaymentMethodCreate,
        update_schema=schemas.PaymentMethodUpdate,
        read_schema=schemas.PaymentMethodRead,
        prefix="/api/v1/payment-methods",
        tags=["payment-methods"],
    )
)
app.include_router(
    make_crud_router(
        model=models.Payment,
        create_schema=schemas.PaymentCreate,
        update_schema=schemas.PaymentUpdate,
        read_schema=schemas.PaymentRead,
        prefix="/api/v1/payments",
        tags=["payments"],
        company_scoped=False,
    )
)
app.include_router(
    make_crud_router(
        model=models.Webhook,
        create_schema=schemas.WebhookCreate,
        update_schema=schemas.WebhookUpdate,
        read_schema=schemas.WebhookRead,
        prefix="/api/v1/webhooks",
        tags=["webhooks"],
    )
)
