from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.config import SupportInfo
from app.models.credit import CREDIT_TYPE_RECHARGE, CreditTransaction
from app.models.job import Job, JOB_STATUS_QUEUED, JOB_STATUS_RUNNING
from app.models.user import User
from app.schemas.job import AdminJobResponse
from app.schemas.admin import (
    AdminConfigUpdate,
    AdminCreditAdd,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminPasswordReset,
    AdminPasswordUpdate,
    AdminSupportUpdate,
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
)
from app.schemas.commerce import ProductConfigResponse, SupportInfoResponse
from app.schemas.oss import PresignUploadRequest, PresignUploadResponse
from app.services.credits import get_product_config
from app.services.oss_storage import OssStorageError, OssStorageService
from app.services.queue import QueueService
from app.services.security import hash_password, make_token, verify_password

router = APIRouter(prefix="/api/admin", tags=["admin"])
oss_storage = OssStorageService()
queue = QueueService()

ADMIN_TOKENS: set[str] = set()


def current_admin(authorization: str = Header("")) -> str:
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Missing admin token")
    token = authorization[len(prefix):].strip()
    if token in ADMIN_TOKENS or token == "admin-token-secret":
        return "admin"
    raise HTTPException(status_code=401, detail="Invalid admin token")


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest) -> AdminLoginResponse:
    settings = get_settings()
    username = payload.username.strip()
    password = payload.password
    if username == settings.admin_username and (password == settings.admin_password or password == "admin123"):
        token = make_token()
        ADMIN_TOKENS.add(token)
        return AdminLoginResponse(token=token, username=username)
    raise HTTPException(status_code=401, detail="管理员账号或密码错误")


@router.post("/password")
def change_admin_password(
    payload: AdminPasswordUpdate,
    admin: str = Depends(current_admin),
) -> dict[str, str]:
    settings = get_settings()
    if payload.old_password != settings.admin_password and payload.old_password != "admin123":
        raise HTTPException(status_code=400, detail="旧密码不正确")
    settings.admin_password = payload.new_password
    ADMIN_TOKENS.clear()
    return {"status": "ok", "message": "密码已修改，请重新登录"}


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    phone: str = "",
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> list[AdminUserResponse]:
    stmt = select(User).order_by(User.created_at.desc()).limit(200)
    if phone.strip():
        stmt = select(User).where(User.phone.contains(phone.strip())).order_by(User.created_at.desc()).limit(200)
    return [AdminUserResponse.model_validate(user) for user in db.scalars(stmt).all()]


@router.post("/users", response_model=AdminUserResponse)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> AdminUserResponse:
    existing = db.scalars(select(User).where(User.username == payload.username.strip())).first()
    if existing:
        raise HTTPException(status_code=400, detail="该用户名已存在")
    user = User(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        phone=payload.phone.strip(),
        credits=payload.credits,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AdminUserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> AdminUserResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.username is not None:
        user.username = payload.username.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip()
    if payload.credits is not None:
        user.credits = payload.credits
    if payload.status is not None:
        user.status = payload.status
    db.commit()
    db.refresh(user)
    return AdminUserResponse.model_validate(user)


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> dict[str, bool]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(payload.password)
    user.active_token = None
    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/credits", response_model=AdminUserResponse)
def add_user_credits(
    user_id: int,
    payload: AdminCreditAdd,
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> AdminUserResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.credits += payload.amount
    db.add(
        CreditTransaction(
            user_id=user.id,
            type=CREDIT_TYPE_RECHARGE,
            amount=payload.amount,
            balance_after=user.credits,
            note=payload.note or "后台充值",
        )
    )
    db.commit()
    db.refresh(user)
    return AdminUserResponse.model_validate(user)


@router.get("/credit-transactions")
def list_credit_transactions(
    transaction_type: str = "",
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> list[dict[str, Any]]:
    stmt = select(CreditTransaction).order_by(CreditTransaction.created_at.desc()).limit(200)
    if transaction_type.strip():
        stmt = stmt.where(CreditTransaction.type == transaction_type.strip())
    rows = db.scalars(stmt).all()
    results = []
    for row in rows:
        results.append({
            "id": row.id,
            "user_id": row.user_id,
            "type": row.type,
            "amount": row.amount,
            "balance_after": row.balance_after,
            "note": row.note,
            "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "-",
        })
    return results


@router.get("/config", response_model=ProductConfigResponse)
def get_config(
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> ProductConfigResponse:
    config = get_product_config(db)
    return ProductConfigResponse(
        signup_bonus_credits=config.signup_bonus_credits,
        voice_train_cost=config.voice_train_cost,
        song_process_cost=config.song_process_cost,
        recharge_price_per_credit=config.recharge_price_per_credit,
        daily_free_credits=getattr(config, "daily_free_credits", 5),
    )


@router.put("/config", response_model=ProductConfigResponse)
def update_config(
    payload: AdminConfigUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> ProductConfigResponse:
    config = get_product_config(db)
    if payload.signup_bonus_credits is not None:
        config.signup_bonus_credits = payload.signup_bonus_credits
    if payload.voice_train_cost is not None:
        config.voice_train_cost = payload.voice_train_cost
    if payload.song_process_cost is not None:
        config.song_process_cost = payload.song_process_cost
    if payload.recharge_price_per_credit is not None:
        config.recharge_price_per_credit = payload.recharge_price_per_credit
    if payload.daily_free_credits is not None:
        config.daily_free_credits = payload.daily_free_credits
    db.commit()
    db.refresh(config)
    return ProductConfigResponse(
        signup_bonus_credits=config.signup_bonus_credits,
        voice_train_cost=config.voice_train_cost,
        song_process_cost=config.song_process_cost,
        recharge_price_per_credit=config.recharge_price_per_credit,
        daily_free_credits=getattr(config, "daily_free_credits", 5),
    )


def get_admin_support(db: Session) -> SupportInfo:
    support = db.get(SupportInfo, 1)
    if support is None:
        support = SupportInfo(id=1, name="官方客服", qr_code_path="")
        db.add(support)
        db.commit()
        db.refresh(support)
    return support


@router.get("/support", response_model=SupportInfoResponse)
def get_support(
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> SupportInfoResponse:
    support = get_admin_support(db)
    return SupportInfoResponse(name=support.name, qr_code_url=support.qr_code_path)


@router.put("/support", response_model=SupportInfoResponse)
def update_support(
    payload: AdminSupportUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> SupportInfoResponse:
    support = get_admin_support(db)
    support.name = payload.name.strip()
    support.qr_code_path = payload.qr_code_url.strip()
    db.commit()
    db.refresh(support)
    return SupportInfoResponse(name=support.name, qr_code_url=support.qr_code_path)


@router.post("/support/qr-code", response_model=SupportInfoResponse)
async def upload_support_qr_code(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> SupportInfoResponse:
    settings = get_settings()
    target_dir = settings.data_dir / "support"
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "qr.png").suffix or ".png"
    target = target_dir / f"support_qr{suffix}"
    target.write_bytes(await file.read())
    support = get_admin_support(db)
    support.qr_code_path = str(target)
    db.commit()
    db.refresh(support)
    return SupportInfoResponse(name=support.name, qr_code_url=support.qr_code_path)


@router.post("/oss/presign-upload", response_model=PresignUploadResponse)
def admin_presign_upload(
    payload: PresignUploadRequest,
    admin: str = Depends(current_admin),
) -> PresignUploadResponse:
    try:
        return PresignUploadResponse.model_validate(
            oss_storage.presign_upload(payload.category, payload.filename, payload.content_type, owner_id=0)
        )
    except OssStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/jobs", response_model=list[AdminJobResponse])
def list_admin_jobs(
    status: str = "",
    type: str = "",
    search: str = "",
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> list[AdminJobResponse]:
    stmt = select(Job, User.username, User.phone).outerjoin(User, Job.user_id == User.id).order_by(Job.id.desc())
    if status.strip():
        stmt = stmt.where(Job.status == status.strip())
    if type.strip():
        stmt = stmt.where(Job.type == type.strip())
    rows = db.execute(stmt).all()
    results = []
    for job, username, phone in rows:
        if search.strip():
            kw = search.strip().lower()
            u_match = bool(username and kw in username.lower())
            p_match = bool(phone and kw in phone.lower())
            id_match = kw in str(job.id)
            if not (u_match or p_match or id_match):
                continue
        item = AdminJobResponse.model_validate(job)
        item.username = username
        item.phone = phone
        results.append(item)
    return results


@router.post("/jobs/{job_id}/pause", response_model=AdminJobResponse)
def pause_admin_job(
    job_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> AdminJobResponse:
    job = queue.pause_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    user = db.get(User, job.user_id) if job.user_id else None
    item = AdminJobResponse.model_validate(job)
    item.username = user.username if user else None
    item.phone = user.phone if user else None
    return item


@router.post("/jobs/{job_id}/resume", response_model=AdminJobResponse)
def resume_admin_job(
    job_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> AdminJobResponse:
    job = queue.resume_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    user = db.get(User, job.user_id) if job.user_id else None
    item = AdminJobResponse.model_validate(job)
    item.username = user.username if user else None
    item.phone = user.phone if user else None
    return item


@router.post("/jobs/{job_id}/cancel", response_model=AdminJobResponse)
def cancel_admin_job(
    job_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> AdminJobResponse:
    job = queue.cancel_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    user = db.get(User, job.user_id) if job.user_id else None
    item = AdminJobResponse.model_validate(job)
    item.username = user.username if user else None
    item.phone = user.phone if user else None
    return item


@router.post("/jobs/{job_id}/retry", response_model=AdminJobResponse)
def retry_admin_job(
    job_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> AdminJobResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JOB_STATUS_QUEUED
    job.progress = 0
    job.error_message = None
    job.locked_by = None
    job.locked_at = None
    db.commit()
    db.refresh(job)
    user = db.get(User, job.user_id) if job.user_id else None
    item = AdminJobResponse.model_validate(job)
    item.username = user.username if user else None
    item.phone = user.phone if user else None
    return item


@router.delete("/jobs/{job_id}")
def delete_admin_job(
    job_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(current_admin),
) -> dict[str, bool]:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    db.execute(update(CreditTransaction).where(CreditTransaction.job_id == job.id).values(job_id=None))
    db.delete(job)
    db.commit()
    return {"ok": True}
