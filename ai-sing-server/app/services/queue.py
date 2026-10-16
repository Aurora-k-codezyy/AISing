import logging
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import (
    JOB_STATUS_FAILED,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCESS,
    JOB_TYPE_VOICE_TRAIN,
    Job,
)

logger = logging.getLogger(__name__)

def utc_now() -> datetime:
    return datetime.now().replace(microsecond=0)

class QueueService:
    def create_job(
        self,
        db: Session,
        user_id: int | None,
        job_type: str,
        input_path: str,
        metadata_json: str | None = None,
    ) -> Job:
        job = Job(
            user_id=user_id,
            type=job_type,
            status=JOB_STATUS_QUEUED,
            progress=0,
            input_path=input_path,
            metadata_json=metadata_json,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def get_job(self, db: Session, job_id: int) -> Job | None:
        return db.get(Job, job_id)

    def list_jobs(self, db: Session, user_id: int | None = None) -> list[Job]:
        stmt = select(Job).order_by(Job.created_at.desc()).limit(100)
        if user_id is not None:
            stmt = select(Job).where(Job.user_id == user_id).order_by(Job.created_at.desc()).limit(100)
        return list(db.scalars(stmt).all())

    def latest_successful_voice_model(self, db: Session, user_id: int | None) -> Job | None:
        stmt = (
            select(Job)
            .where(Job.type == JOB_TYPE_VOICE_TRAIN)
            .where(Job.status == JOB_STATUS_SUCCESS)
            .where(Job.output_path.is_not(None))
            .order_by(Job.finished_at.desc(), Job.created_at.desc())
            .limit(1)
        )
        if user_id is not None:
            stmt = stmt.where(Job.user_id == user_id)
        return db.scalars(stmt).first()

    def claim_next(self, db: Session, worker_id: str) -> Job | None:
        stmt = select(Job).where(Job.status == JOB_STATUS_QUEUED).order_by(Job.created_at.asc()).limit(1)
        job = db.scalars(stmt).first()
        if job is None:
            return None
        job.status = JOB_STATUS_RUNNING
        job.started_at = utc_now()
        job.locked_by = worker_id
        job.locked_at = utc_now()
        db.commit()
        db.refresh(job)
        return job

    def update_progress(self, db: Session, job_id: int, progress: int) -> None:
        job = db.get(Job, job_id)
        if job and job.status == JOB_STATUS_RUNNING:
            job.progress = progress
            db.commit()

    def mark_success(self, db: Session, job_id: int, output_path: str) -> None:
        job = db.get(Job, job_id)
        if job:
            job.status = JOB_STATUS_SUCCESS
            job.progress = 100
            job.output_path = output_path
            job.finished_at = utc_now()
            db.commit()

    def mark_failed(self, db: Session, job_id: int, error_message: str) -> None:
        job = db.get(Job, job_id)
        if job:
            job.status = JOB_STATUS_FAILED
            job.error_message = error_message
            job.finished_at = utc_now()
            db.commit()

    def pause_job(self, db: Session, job_id: int, user_id: int | None = None) -> Job | None:
        job = db.get(Job, job_id)
        if job is None:
            return None
        if user_id is not None and job.user_id != user_id:
            return None
        if job.status in (JOB_STATUS_QUEUED, JOB_STATUS_RUNNING):
            job.status = "paused"
            db.commit()
            db.refresh(job)
        return job

    def resume_job(self, db: Session, job_id: int, user_id: int | None = None) -> Job | None:
        job = db.get(Job, job_id)
        if job is None:
            return None
        if user_id is not None and job.user_id != user_id:
            return None
        if job.status == "paused":
            job.status = JOB_STATUS_QUEUED
            db.commit()
            db.refresh(job)
        return job

    def cancel_job(self, db: Session, job_id: int, user_id: int | None = None) -> Job | None:
        job = db.get(Job, job_id)
        if job is None:
            return None
        if user_id is not None and job.user_id != user_id:
            return None
        job.status = "cancelled"
        job.finished_at = utc_now()
        db.commit()
        db.refresh(job)
        return job
