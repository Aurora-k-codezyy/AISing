import json
import logging
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.config import ProductConfig
from app.models.credit import CREDIT_TYPE_CONSUME, CreditTransaction
from app.models.job import JOB_TYPE_SONG_PROCESS, Job
from app.models.user import User

logger = logging.getLogger(__name__)


def get_product_config(db: Session) -> ProductConfig:
    config = db.get(ProductConfig, 1)
    if config is None:
        config = ProductConfig(
            id=1,
            signup_bonus_credits=480,
            voice_train_cost=450,
            song_process_cost=1,
            recharge_price_per_credit=1,
            daily_free_credits=5,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def get_daily_free_remaining(db: Session, user: User) -> int:
    config = get_product_config(db)
    daily_quota = getattr(config, "daily_free_credits", 5)
    if daily_quota <= 0:
        return 0

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Query today's song_process jobs submitted by this user
    jobs = db.scalars(
        select(Job)
        .where(Job.user_id == user.id)
        .where(Job.type == JOB_TYPE_SONG_PROCESS)
        .where(Job.created_at >= today_start)
    ).all()

    online_count = 0
    for j in jobs:
        is_local = False
        if j.metadata_json:
            try:
                m = json.loads(j.metadata_json) if isinstance(j.metadata_json, str) else j.metadata_json
                if isinstance(m, dict):
                    if m.get("is_local") or m.get("processing_mode") == "local":
                        is_local = True
                    opts = m.get("processing_options")
                    if isinstance(opts, dict) and (opts.get("is_local") or opts.get("processing_mode") == "local"):
                        is_local = True
            except Exception:
                pass
        if not is_local:
            online_count += 1

    remaining = max(0, daily_quota - online_count)
    return remaining


def consume_credits(db: Session, user: User, amount: int, note: str, job_id: int | None = None) -> bool:
    if amount <= 0:
        return True
    if user.credits < amount:
        raise HTTPException(status_code=402, detail=f"积分不足，本次操作需要 {amount} 积分，当前仅有 {user.credits} 积分")
    user.credits -= amount
    tx = CreditTransaction(
        user_id=user.id,
        type=CREDIT_TYPE_CONSUME,
        amount=-amount,
        balance_after=user.credits,
        note=note,
        job_id=job_id,
    )
    db.add(tx)
    return True
