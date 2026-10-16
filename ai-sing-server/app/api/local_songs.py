from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Any
import json
from pathlib import Path

from app.api.auth import current_user
from app.models.user import User

router = APIRouter(prefix="/api", tags=["local_songs"])

# Simple in-memory / file-based storage for local songs cache per user
DATA_FILE = Path("data/local_songs_db.json")


def _load_data() -> dict:
    if DATA_FILE.is_file():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"songs": {}, "categories": {}}


def _save_data(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/local-songs")
def list_local_songs(user: User = Depends(current_user)) -> list[dict]:
    data = _load_data()
    user_songs = data.get("songs", {}).get(str(user.id), {})
    return list(user_songs.values())


@router.post("/local-songs")
def sync_local_song(payload: dict, user: User = Depends(current_user)) -> dict:
    data = _load_data()
    uid = str(user.id)
    if uid not in data.get("songs", {}):
        data.setdefault("songs", {})[uid] = {}
    local_id = str(payload.get("local_id") or payload.get("id") or len(data["songs"][uid]) + 1)
    payload["id"] = int(local_id)
    data["songs"][uid][local_id] = payload
    _save_data(data)
    return payload


@router.patch("/local-songs/{local_id}")
def update_local_song(local_id: int, updates: dict, user: User = Depends(current_user)) -> dict:
    data = _load_data()
    uid = str(user.id)
    lid = str(local_id)
    song = data.get("songs", {}).get(uid, {}).get(lid, {})
    song.update(updates)
    data.setdefault("songs", {}).setdefault(uid, {})[lid] = song
    _save_data(data)
    return song


@router.delete("/local-songs/{local_id}", status_code=204)
def delete_local_song(local_id: int, user: User = Depends(current_user)) -> Response:
    data = _load_data()
    uid = str(user.id)
    lid = str(local_id)
    if uid in data.get("songs", {}) and lid in data["songs"][uid]:
        del data["songs"][uid][lid]
        _save_data(data)
    return Response(status_code=204)


@router.get("/local-song-categories")
def list_local_song_categories(user: User = Depends(current_user)) -> list[str]:
    data = _load_data()
    uid = str(user.id)
    cats = data.get("categories", {}).get(uid, ["默认"])
    if "默认" not in cats:
        cats.insert(0, "默认")
    return cats


@router.post("/local-song-categories")
def add_local_song_category(payload: dict, user: User = Depends(current_user)) -> dict:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name cannot be empty")
    data = _load_data()
    uid = str(user.id)
    cats = data.setdefault("categories", {}).setdefault(uid, ["默认"])
    if name not in cats:
        cats.append(name)
        _save_data(data)
    return {"name": name}


@router.delete("/local-song-categories/{name}", status_code=204)
def delete_local_song_category(name: str, user: User = Depends(current_user)) -> Response:
    data = _load_data()
    uid = str(user.id)
