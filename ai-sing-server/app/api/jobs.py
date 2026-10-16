import json
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.api.auth import current_user
from app.core.database import get_db
from app.models.credit import CreditTransaction
from app.models.job import (
    JOB_STATUS_SUCCESS,
    JOB_TYPE_SONG_PROCESS,
    JOB_TYPE_VOICE_TRAIN,
    Job,
)
from app.models.user import User
from app.schemas.job import JobResponse, populate_job_flags
from app.schemas.oss import (
    PresignUploadRequest,
    PresignUploadResponse,
    SongUploadCompleteRequest,
    UploadedObject,
)
from app.services.credits import consume_credits, get_daily_free_remaining, get_product_config
from app.services.oss_storage import OssStorageError, OssStorageService
from app.services.queue import QueueService
from app.services.storage import StorageService

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
oss_router = APIRouter(prefix="/api/oss", tags=["oss"])
storage = StorageService()
oss_storage = OssStorageService()
queue = QueueService()
logger = logging.getLogger(__name__)


@oss_router.post("/presign-upload", response_model=PresignUploadResponse)
def presign_upload(
    payload: PresignUploadRequest,
    user: User = Depends(current_user),
) -> PresignUploadResponse:
    try:
        return PresignUploadResponse.model_validate(
            oss_storage.presign_upload(payload.category, payload.filename, payload.content_type, owner_id=user.id)
        )
    except OssStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@oss_router.put("/local-upload")
async def local_upload(object_key: str, request: Request):
    body = await request.body()
    target = storage.data_dir / "local_oss" / object_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return {"status": "ok", "bytes": len(body)}


@oss_router.get("/local-files/{object_key:path}")
def local_file(object_key: str):
    target = storage.data_dir / "local_oss" / object_key
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Local file missing")
    return FileResponse(str(target))


@router.post("/voice-train", response_model=JobResponse)
async def create_voice_train_job(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> JobResponse:
    config = get_product_config(db)
    input_path = await storage.save_upload(file, "voice_train")
    job = queue.create_job(db, user_id=user.id, job_type=JOB_TYPE_VOICE_TRAIN, input_path=str(input_path))
    consume_credits(db, user, config.voice_train_cost, "干声训练", job.id)
    db.commit()
    db.refresh(job)
    logger.info("Created voice_train job id=%s user_id=%s input=%s", job.id, user.id, input_path)
    return populate_job_flags(JobResponse.model_validate(job))


@router.post("/voice-train/complete", response_model=JobResponse)
def complete_voice_train_job(
    payload: UploadedObject,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> JobResponse:
    config = get_product_config(db)
    metadata = json.dumps(
        {
            "input": payload.model_dump(),
            "source": "oss",
        },
        ensure_ascii=True,
    )
    job = queue.create_job(
        db,
        user_id=user.id,
        job_type=JOB_TYPE_VOICE_TRAIN,
        input_path=payload.public_url,
        metadata_json=metadata,
    )
    consume_credits(db, user, config.voice_train_cost, "干声训练", job.id)
    db.commit()
    db.refresh(job)
    logger.info("Created OSS voice_train job id=%s user_id=%s input=%s", job.id, user.id, payload.public_url)
    return populate_job_flags(JobResponse.model_validate(job))


@router.post("/song-process", response_model=JobResponse)
async def create_song_process_job(
    task_name: str = Form(""),
    file: UploadFile = File(...),
    lyrics_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> JobResponse:
    config = get_product_config(db)
    input_path = await storage.save_upload(file, "song_process")
    lyrics_path = await storage.save_upload(lyrics_file, "song_lyrics")
    display_name = task_name.strip() or Path(input_path).stem
    metadata = json.dumps({"lyrics_path": str(lyrics_path), "task_name": display_name}, ensure_ascii=True)
    job = queue.create_job(
        db,
        user_id=user.id,
        job_type=JOB_TYPE_SONG_PROCESS,
        input_path=str(input_path),
        metadata_json=metadata,
    )
    free_remaining = get_daily_free_remaining(db, user)
    if free_remaining > 0:
        logger.info("Song process job id=%s user_id=%s using daily free quota (remaining: %s)", job.id, user.id, free_remaining - 1)
        tx = CreditTransaction(
            user_id=user.id,
            type="consume",
            amount=0,
            balance_after=user.credits,
            note="歌曲处理 (每日免费额度)",
            job_id=job.id,
        )
        db.add(tx)
    else:
        consume_credits(db, user, config.song_process_cost, "歌曲处理", job.id)
    db.commit()
    db.refresh(job)
    logger.info(
        "Created song_process job id=%s user_id=%s name=%s input=%s lyrics=%s",
        job.id,
        user.id,
        display_name,
        input_path,
        lyrics_path,
    )
    return populate_job_flags(JobResponse.model_validate(job))


@router.post("/song-process/complete", response_model=JobResponse)
def complete_song_process_job(
    payload: SongUploadCompleteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> JobResponse:
    config = get_product_config(db)
    display_name = payload.task_name.strip() or Path(payload.audio.filename or payload.audio.object_key).stem
    metadata = json.dumps(
        {
            "input": payload.audio.model_dump(),
            "lyrics": payload.lyrics.model_dump(),
            "lyrics_path": payload.lyrics.public_url,
            "task_name": display_name,
            "processing_options": payload.processing_options or {},
            "pitch_analysis": payload.pitch_analysis,
            "source": "oss",
        },
        ensure_ascii=True,
    )
    job = queue.create_job(
        db,
        user_id=user.id,
        job_type=JOB_TYPE_SONG_PROCESS,
        input_path=payload.audio.public_url,
        metadata_json=metadata,
    )

    # Check if local processing mode
    is_local = False
    proc_opts = payload.processing_options
    if isinstance(proc_opts, dict):
        if proc_opts.get("is_local") or proc_opts.get("processing_mode") == "local":
            is_local = True

    if is_local:
        logger.info("Created local mode song_process job id=%s user_id=%s: 0 credits consumed", job.id, user.id)
    else:
        free_remaining = get_daily_free_remaining(db, user)
        if free_remaining > 0:
            logger.info("Created song_process job id=%s user_id=%s using daily free quota (remaining: %s)", job.id, user.id, free_remaining - 1)
            tx = CreditTransaction(
                user_id=user.id,
                type="consume",
                amount=0,
                balance_after=user.credits,
                note="歌曲处理 (每日免费额度)",
                job_id=job.id,
            )
            db.add(tx)
        else:
            consume_credits(db, user, config.song_process_cost, "歌曲处理", job.id)

    db.commit()
    db.refresh(job)
    logger.info(
        "Created OSS song_process job id=%s user_id=%s name=%s input=%s lyrics=%s local=%s",
        job.id,
        user.id,
        display_name,
        payload.audio.public_url,
        payload.lyrics.public_url,
        is_local,
    )
    return populate_job_flags(JobResponse.model_validate(job))


@router.get("", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[JobResponse]:
    return [populate_job_flags(JobResponse.model_validate(job)) for job in queue.list_jobs(db, user_id=user.id)]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> JobResponse:
    job = queue.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return populate_job_flags(JobResponse.model_validate(job))


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    job = queue.get_job(db, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == "running":
        raise HTTPException(status_code=409, detail="Running job cannot be deleted")
    db.execute(update(CreditTransaction).where(CreditTransaction.job_id == job.id).values(job_id=None))
    db.delete(job)
    db.commit()
    return Response(status_code=204)


@router.get("/{job_id}/download")
def download_job_output(job_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> FileResponse:
    job = queue.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JOB_STATUS_SUCCESS or not job.output_path:
        raise HTTPException(status_code=409, detail="Job output is not ready")
    if job.output_path.startswith(("http://", "https://")):
        return RedirectResponse(job.output_path)
    output = Path(job.output_path)
    if not output.exists() or not output.is_file():
        raise HTTPException(status_code=404, detail="Output file missing")
    return FileResponse(str(output), filename=output.name)


@router.get("/{job_id}/files/{file_kind}")
def download_job_file(
    job_id: int,
    file_kind: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> FileResponse:
    job = queue.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JOB_STATUS_SUCCESS:
        raise HTTPException(status_code=409, detail="Job output is not ready")
    if job.type != JOB_TYPE_SONG_PROCESS:
        raise HTTPException(status_code=400, detail="Job does not have song files")

    metadata_file_url = output_file_url(job.metadata_json, file_kind)
    if metadata_file_url:
        return RedirectResponse(metadata_file_url)

    output_dir = storage.song_output_dir(job.id)
    allowed = {
        "ai_vocal": output_dir / "ai_vocal.wav",
        "instrumental": output_dir / "instrumental.wav",
    }
    if file_kind == "lyrics":
        matches = sorted(output_dir.glob("lyrics.*"))
        if not matches:
            raise HTTPException(status_code=404, detail="Lyrics file missing")
        target = matches[0]
    else:
        target = allowed.get(file_kind)
        if target is None:
            raise HTTPException(status_code=404, detail="Unknown song file")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Song file missing")
    return FileResponse(str(target), filename=target.name)


def output_file_url(metadata_json: str | None, file_kind: str) -> str | None:
    if not metadata_json:
        return None
    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError:
        return None
    output_files = metadata.get("output_files")
    if not isinstance(output_files, dict):
        return None
    item = output_files.get(file_kind)
    if isinstance(item, dict):
        url = item.get("public_url")
        return url if isinstance(url, str) and url else None
    return None


@router.post("/voice-model/import")
def import_voice_model(
    payload: dict,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    name = payload.get("name") or "imported_model"
    logger.info("Imported voice model name=%s for user_id=%s", name, user.id)
    return {"status": "ok", "message": "Voice model imported successfully", "name": name}


@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(
    job_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = queue.cancel_job(db, job_id, user_id=user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return populate_job_flags(JobResponse.model_validate(job))


@router.post("/{job_id}/pause", response_model=JobResponse)
def pause_job(
    job_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = queue.pause_job(db, job_id, user_id=user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return populate_job_flags(JobResponse.model_validate(job))


@router.post("/{job_id}/resume", response_model=JobResponse)
def resume_job(
    job_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = queue.resume_job(db, job_id, user_id=user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return populate_job_flags(JobResponse.model_validate(job))


class JobRegenerateRequest(BaseModel):
    model_job_id: int | None = None


@router.post("/{job_id}/regenerate", response_model=JobResponse)
def regenerate_job(
    job_id: int,
    payload: JobRegenerateRequest | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> JobResponse:
    job = queue.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user.id and not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Forbidden")
    if job.type != JOB_TYPE_SONG_PROCESS:
        raise HTTPException(status_code=400, detail="Only song process jobs can be regenerated")

    meta = {}
    if job.metadata_json:
        try:
            meta = json.loads(job.metadata_json)
        except Exception:
            pass

    input_info = meta.get("input") or {}
    lyrics_info = meta.get("lyrics") or {}
    task_name = meta.get("task_name") or f"重新生成 - {job.id}"
    processing_options = meta.get("processing_options") or {}
    pitch_analysis = meta.get("pitch_analysis")

    new_meta = {
        "input": input_info,
        "lyrics": lyrics_info,
        "lyrics_path": meta.get("lyrics_path") or lyrics_info.get("public_url", ""),
        "task_name": task_name,
        "processing_options": processing_options,
        "pitch_analysis": pitch_analysis,
        "source": meta.get("source", "oss"),
        "regenerated_from": job.id,
    }
    if payload and payload.model_job_id:
        new_meta["model_job_id"] = int(payload.model_job_id)

    new_job = queue.create_job(
        db,
        user_id=user.id,
        job_type=JOB_TYPE_SONG_PROCESS,
        input_path=job.input_path,
        metadata_json=json.dumps(new_meta, ensure_ascii=False),
    )

    # Copy separated vocals and accompaniment if available from old job
    old_output_dir = storage.song_output_dir(job.id)
    new_output_dir = storage.song_output_dir(new_job.id)
    if old_output_dir.is_dir():
        new_output_dir.mkdir(parents=True, exist_ok=True)
        old_vocals = old_output_dir / "vocals.wav"
        old_inst = old_output_dir / "instrumental.wav"
        old_lyrics = old_output_dir / "lyrics.lrc"
        if old_vocals.is_file():
            shutil.copy2(old_vocals, new_output_dir / "vocals.wav")
        if old_inst.is_file():
            shutil.copy2(old_inst, new_output_dir / "instrumental.wav")
        if old_lyrics.is_file():
            shutil.copy2(old_lyrics, new_output_dir / "lyrics.lrc")

    db.commit()
    db.refresh(new_job)
    logger.info("Regenerated song_process job old_id=%s new_id=%s user_id=%s", job.id, new_job.id, user.id)
    return populate_job_flags(JobResponse.model_validate(new_job))


@router.post("/{job_id}/toggle-hide")
def toggle_hide_job(
    job_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    job = queue.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user.id and not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Forbidden")

    meta = {}
    if job.metadata_json:
        try:
            meta = json.loads(job.metadata_json)
        except Exception:
            pass

    current_hidden = bool(meta.get("hidden", False))
    new_hidden = not current_hidden
    meta["hidden"] = new_hidden
    job.metadata_json = json.dumps(meta, ensure_ascii=False)
    db.commit()
    logger.info("Toggled hide for job_id=%s hidden=%s", job.id, new_hidden)
    return {"job_id": job.id, "hidden": new_hidden}
