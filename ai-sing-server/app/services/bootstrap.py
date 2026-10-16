from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.admin import Admin
from app.models.config import ProductConfig, SupportInfo
from app.services.security import hash_password


def ensure_defaults(db: Session, settings: Settings) -> None:
    admin = db.scalars(select(Admin).where(Admin.username == settings.admin_username)).first()
    if admin is None:
        db.add(Admin(username=settings.admin_username, password_hash=hash_password(settings.admin_password)))
    if db.get(ProductConfig, 1) is None:
        db.add(ProductConfig(id=1))
    if db.get(SupportInfo, 1) is None:
        db.add(SupportInfo(id=1))
    db.commit()

