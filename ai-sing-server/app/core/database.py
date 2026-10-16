from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models import job as _job
from app.models import user as _user
from app.models import credit as _credit
from app.models import config as _config
from app.models import admin as _admin
from app.models.base import Base
from app.services.schema_migration import sync_schema


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    sync_schema(engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

