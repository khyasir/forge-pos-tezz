from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_missing_columns(bind=None) -> list[str]:
    """Tiny forward-only migration: ALTER TABLE ... ADD COLUMN for model columns
    that an older database does not have yet. Safe to run on every startup."""
    from sqlalchemy import inspect, text

    bind = bind or engine
    insp = inspect(bind)
    added = []
    existing_tables = set(insp.get_table_names())
    with bind.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                coltype = col.type.compile(dialect=bind.dialect)
                default = ""
                if col.default is not None and getattr(col.default, "is_scalar", False):
                    val = col.default.arg
                    if isinstance(val, bool):
                        default = f" DEFAULT {'TRUE' if val else 'FALSE'}" if bind.dialect.name != "sqlite" else f" DEFAULT {int(val)}"
                    elif isinstance(val, (int, float)):
                        default = f" DEFAULT {val}"
                    elif isinstance(val, str):
                        default = " DEFAULT '" + val.replace("'", "''") + "'"
                conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} {coltype}{default}'))
                added.append(f"{table.name}.{col.name}")
    return added
