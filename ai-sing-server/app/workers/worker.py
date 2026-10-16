import asyncio
import contextlib
import json
import logging
import socket
from pathlib import Path

from app.core.database import SessionLocal
from app.models.job import JOB_TYPE_SONG_PROCESS, JOB_TYPE_VOICE_TRAIN
from app.models.job import Job
from app.services.oss_storage import OssObject, OssStorageService
from app.services.pipelines import PlaceholderPipelines, RealAudioPipelines
from app.services.queue import QueueService
from app.services.storage import StorageService


logger = logging.getLogger(__name__)


class BackgroundWorker:
    def __init__(self) -> None:
        self.worker_id = f"{socket.gethostname()}-worker"
        self.queue = QueueService()
        rvc_cli_candidates = [
            Path(r"E:\miscol\AISing\rvc-cli\rvc_cli.py"),
            Path(__file__).resolve().parents[3] / "rvc-cli" / "rvc_cli.py",
            Path("/opt/rvc-cli/rvc_cli.py"),
        ]
        rvc_cli = next((p for p in rvc_cli_candidates if p.exists()), None)
        if rvc_cli:
            logger.info("Using RealAudioPipelines with RVC CLI at %s", rvc_cli)
            self.pipelines = RealAudioPipelines()
        else:
            logger.info("RVC CLI not found; using PlaceholderPipelines for local development")
            self.pipelines = PlaceholderPipelines()
        self.storage = StorageService()
        self.oss_storage = OssStorageService()
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        logger.info("Starting background worker id=%s", self.worker_id)
        self._stopped.clear()
        self._task = asyncio.create_task(self.run())

    async def stop(self) -> None:
        logger.info("Stopping background worker id=%s", self.worker_id)
        self._stopped.set()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def run(self) -> None:
        while not self._stopped.is_set():
            processed = await asyncio.to_thread(self.process_one)
            if not processed:
                await asyncio.sleep(1.0)

    def process_one(self) -> bool:
        with SessionLocal() as db:
            job = self.queue.claim_next(db, self.worker_id)
            if job is None:
                return False
            logger.info("Claimed job id=%s type=%s user_id=%s input=%s", job.id, job.type, job.user_id, job.input_path)
            try:

                def progress(value: int) -> None:
                    with SessionLocal() as progress_db:
                        self.queue.update_progress(progress_db, job.id, value)
                    logger.info("Job progress id=%s progress=%s", job.id, value)

                if job.type == JOB_TYPE_VOICE_TRAIN:
                    input_path = self.localize_uploaded_input(job, "voice_train")
                    output_path = self.pipelines.run_voice_training(job.id, input_path, progress)
                elif job.type == JOB_TYPE_SONG_PROCESS:
                    metadata = self.metadata_dict(job.metadata_json)
                    proc_opts = metadata.get("processing_options")
                    model_job_id = metadata.get("model_job_id") or (proc_opts.get("model_job_id") if isinstance(proc_opts, dict) else None)
                    model_job = None
                    if model_job_id:
                        try:
                            model_job = db.get(Job, int(model_job_id))
                        except Exception:
                            model_job = None
                    if not model_job:
                        model_job = self.queue.latest_successful_voice_model(db, job.user_id)
                    model_path = self.localize_model_output(model_job) if model_job else None
                    input_path = self.localize_uploaded_input(job, "song")
                    lyrics_path = self.localize_lyrics(job)
                    output_path = self.pipelines.run_song_processing(
                        job.id,
                        input_path,
                        progress,
                        model_path,
                        lyrics_path,
                    )
                else:
                    raise ValueError(f"Unknown job type: {job.type}")

                public_output_path = self.upload_outputs_and_update_metadata(job, output_path)
                self.queue.mark_success(db, job.id, public_output_path)
                logger.info("Job succeeded id=%s output=%s", job.id, public_output_path)
            except Exception as exc:
                with SessionLocal() as check_db:
                    latest = check_db.get(Job, job.id)
                    if latest and latest.status in ("cancelled", "paused"):
                        logger.info("Job id=%s was %s by user or admin; stopping cleanly", job.id, latest.status)
                        return True
                logger.exception("Job failed id=%s type=%s error=%s", job.id, job.type, exc)
                self.queue.mark_failed(db, job.id, str(exc))
            return True

    def metadata_dict(self, metadata_json: str | None) -> dict:
        if not metadata_json:
            return {}
        try:
            value = json.loads(metadata_json)
        except json.JSONDecodeError:
            logger.warning("Ignoring invalid job metadata json: %s", metadata_json)
            return {}
        return value if isinstance(value, dict) else {}

    def localize_uploaded_input(self, job: Job, category: str) -> str:
        metadata = self.metadata_dict(job.metadata_json)
        uploaded = metadata.get("input") if isinstance(metadata.get("input"), dict) else {}
        source = uploaded.get("public_url") or uploaded.get("object_key") or job.input_path
        if not isinstance(source, str) or not source.startswith(("http://", "https://")) and Path(source).is_file():
            return job.input_path
        filename = uploaded.get("filename") if isinstance(uploaded.get("filename"), str) else Path(job.input_path).name
        suffix = Path(filename).suffix or ".bin"
        target = self.storage.oss_cache_dir(job.id) / f"{category}_input{suffix}"
        return str(self.oss_storage.download_to_file(source, target))

    def localize_lyrics(self, job: Job) -> str | None:
        metadata = self.metadata_dict(job.metadata_json)
        lyrics = metadata.get("lyrics") if isinstance(metadata.get("lyrics"), dict) else {}
        source = lyrics.get("public_url") or lyrics.get("object_key") or metadata.get("lyrics_path")
        if not isinstance(source, str) or not source:
            return None
        if not source.startswith(("http://", "https://")) and Path(source).is_file():
            return source
        filename = lyrics.get("filename") if isinstance(lyrics.get("filename"), str) else "lyrics.lrc"
        suffix = Path(filename).suffix or ".lrc"
        target = self.storage.oss_cache_dir(job.id) / f"lyrics{suffix}"
        return str(self.oss_storage.download_to_file(source, target))

    def localize_model_output(self, model_job: Job | None) -> str | None:
        if model_job is None or not model_job.output_path:
            return None
        if not model_job.output_path.startswith(("http://", "https://")) and Path(model_job.output_path).is_file():
            return model_job.output_path
        metadata = self.metadata_dict(model_job.metadata_json)
        output_files = metadata.get("output_files") if isinstance(metadata.get("output_files"), dict) else {}
        model = output_files.get("model") if isinstance(output_files.get("model"), dict) else {}
        index = output_files.get("index") if isinstance(output_files.get("index"), dict) else {}
        source = model.get("public_url") or model.get("object_key") or model_job.output_path
        cache_dir = self.storage.oss_cache_dir(model_job.id)
        model_target = cache_dir / "model.pth"
        localized_model = self.oss_storage.download_to_file(source, model_target)
        index_source = index.get("public_url") or index.get("object_key")
        if index_source:
            self.oss_storage.download_to_file(index_source, cache_dir / "model.index")
        return str(localized_model)

    def upload_outputs_and_update_metadata(self, job: Job, output_path: str) -> str:
        if job.type == JOB_TYPE_VOICE_TRAIN:
            return self.upload_voice_outputs(job, output_path)
        if job.type == JOB_TYPE_SONG_PROCESS:
            return self.upload_song_outputs(job, output_path)
        return output_path

    def upload_voice_outputs(self, job: Job, output_path: str) -> str:
        model_path = Path(output_path)
        output_dir = model_path.parent
        files: dict[str, OssObject] = {"model": self.oss_storage.upload_file(model_path, "outputs/models", job.user_id)}
        index_path = output_dir / "model.index"
        manifest_path = output_dir / "manifest.txt"
        if index_path.exists():
            files["index"] = self.oss_storage.upload_file(index_path, "outputs/models", job.user_id)
        if manifest_path.exists():
            files["manifest"] = self.oss_storage.upload_file(manifest_path, "outputs/models", job.user_id)
        self.merge_output_metadata(job, files)
        return files["model"].public_url

    def upload_song_outputs(self, job: Job, output_path: str) -> str:
        ai_vocal = Path(output_path)
        output_dir = ai_vocal.parent
        files: dict[str, OssObject] = {"ai_vocal": self.oss_storage.upload_file(ai_vocal, "outputs/songs", job.user_id)}
        instrumental = output_dir / "instrumental.wav"
        if instrumental.exists():
            files["instrumental"] = self.oss_storage.upload_file(instrumental, "outputs/songs", job.user_id)
        lyrics = next(iter(sorted(output_dir.glob("lyrics.*"))), None)
        if lyrics and lyrics.exists():
            files["lyrics"] = self.oss_storage.upload_file(lyrics, "outputs/songs", job.user_id)
        self.merge_output_metadata(job, files)
        return files["ai_vocal"].public_url

    def merge_output_metadata(self, job: Job, files: dict[str, OssObject]) -> None:
        metadata = self.metadata_dict(job.metadata_json)
        metadata["output_files"] = {
            name: {"object_key": item.object_key, "public_url": item.public_url}
            for name, item in files.items()
        }
        job.metadata_json = json.dumps(metadata, ensure_ascii=True)

