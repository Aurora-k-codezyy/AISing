import json
import logging
from pathlib import Path
import os
from PySide6.QtCore import Qt, QSettings, QByteArray, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QComboBox,
    QWidget,
)

SVG_REGEN = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
  <path d="M3 3v5h5"/>
  <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>
  <path d="M16 21h5v-5"/>
</svg>"""

SVG_EYE = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
  <circle cx="12" cy="12" r="3"/>
</svg>"""

SVG_EYE_OFF = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/>
  <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/>
  <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/>
  <line x1="2" x2="22" y1="2" y2="22"/>
</svg>"""

SVG_TRASH = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 6h18"/>
  <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>
  <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
  <line x1="10" x2="10" y1="11" y2="17"/>
  <line x1="14" x2="14" y1="11" y2="17"/>
</svg>"""

SVG_PAUSE = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect width="4" height="16" x="6" y="4" rx="1"/>
  <rect width="4" height="16" x="14" y="4" rx="1"/>
</svg>"""

SVG_PLAY = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polygon points="6 3 20 12 6 21 6 3"/>
</svg>"""


def make_monochrome_icon(svg_template, is_dark=False, size=18) -> QIcon:
    normal_color = "#94a3b8" if is_dark else "#475569"
    active_color = "#ffffff" if is_dark else "#0f172a"
    icon = QIcon()
    for mode, color in [(QIcon.Normal, normal_color), (QIcon.Active, active_color)]:
        svg_code = svg_template.format(color=color)
        renderer = QSvgRenderer(QByteArray(svg_code.encode("utf-8")))
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        renderer.render(p)
        p.end()
        icon.addPixmap(pix, mode)
    return icon

logger = logging.getLogger(__name__)


def is_song_hidden(job: dict) -> bool:
    if not job:
        return False
    jid = str(job.get("id", ""))

    # 1. In-memory property
    if job.get("hidden") is True:
        return True

    # 2. Check metadata_json
    raw_meta = job.get("metadata_json")
    if raw_meta:
        try:
            m = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
            if isinstance(m, dict) and m.get("hidden") is True:
                return True
        except Exception:
            pass

    # 3. Check persistent QSettings
    try:
        settings = QSettings("Qingxuan", "HiddenSongs")
        hidden_ids = settings.value("hidden_ids", [])
        if hidden_ids and jid in [str(x) for x in hidden_ids]:
            return True
    except Exception:
        pass

    return False


def toggle_song_hidden(api, job: dict) -> bool:
    jid = int(job.get("id", 0))
    jid_str = str(jid)
    current = is_song_hidden(job)
    new_state = not current

    # 1. Update in-memory
    job["hidden"] = new_state
    raw_meta = job.get("metadata_json")
    if raw_meta:
        try:
            m = json.loads(raw_meta) if isinstance(raw_meta, str) else dict(raw_meta)
            m["hidden"] = new_state
            job["metadata_json"] = json.dumps(m, ensure_ascii=False)
        except Exception:
            pass

    # 2. Update persistent QSettings
    try:
        settings = QSettings("Qingxuan", "HiddenSongs")
        raw_list = settings.value("hidden_ids", [])
        hidden_set = set(str(x) for x in (raw_list if isinstance(raw_list, list) else []))
        if new_state:
            hidden_set.add(jid_str)
        else:
            hidden_set.discard(jid_str)
        settings.setValue("hidden_ids", list(hidden_set))
    except Exception as exc:
        logger.warning("Error saving hidden settings: %s", exc)

    # 3. Sync to server
    try:
        if api and hasattr(api, "toggle_hide_job"):
            api.toggle_hide_job(jid)
    except Exception as exc:
        logger.warning("Server toggle-hide failed: %s", exc)

    return new_state


def get_user_voice_models(api=None, current_jobs=None) -> list[dict]:
    """
    Returns list of user's successful voice models:
    [{"id": job_id, "name": display_name, "created_at": ...}, ...]
    """
    jobs = current_jobs
    if not jobs and api:
        try:
            jobs = api.list_jobs()
        except Exception as exc:
            logger.warning("Failed to list jobs for voice models: %s", exc)
            jobs = []

    models = []
    seen = set()
    for j in (jobs or []):
        if j.get("type") == "voice_train" and str(j.get("status", "")).lower() == "success":
            jid = int(j.get("id", 0))
            if jid in seen:
                continue
            seen.add(jid)

            name = ""
            meta_raw = j.get("metadata_json")
            if meta_raw:
                try:
                    meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                    name = meta.get("task_name") or meta.get("input", {}).get("filename") or ""
                except Exception:
                    pass
            if not name:
                name = f"专属音色 #{jid}"
            else:
                if name.endswith(".wav") or name.endswith(".mp3"):
                    name = name.rsplit(".", 1)[0]
                name = f"{name} (#{jid})"

            models.append({"id": jid, "name": name, "created_at": j.get("created_at", "")})

    models.sort(key=lambda x: x["id"], reverse=True)
    return models


class RegenerateDialog(QDialog):
    """
    Dialog for regenerating a song with multi-voice selection dropdown.
    """

    def __init__(self, parent, job: dict, voice_models: list[dict], song_title: str):
        super().__init__(parent)
        self.setWindowTitle("重新生成歌曲")
        self.setFixedWidth(440)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e293b;
                color: #f8fafc;
            }
            QLabel {
                color: #f8fafc;
                font-size: 13px;
            }
            QComboBox {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                min-height: 28px;
            }
            QComboBox:hover {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #f8fafc;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
                border: 1px solid #334155;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        title_label = QLabel("🔄 重新生成歌曲（音色合成）")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #60a5fa;")
        layout.addWidget(title_label)

        song_info = QLabel(f"歌曲名称：<b style='color:#38bdf8;'>{song_title}</b> (任务 #{job.get('id')})")
        layout.addWidget(song_info)

        tip_label = QLabel("选择合成音色（支持多音色切换）：")
        tip_label.setStyleSheet("font-size: 12px; color: #94a3b8;")
        layout.addWidget(tip_label)

        self.model_combo = QComboBox()

        current_model_id = None
        raw_meta = job.get("metadata_json")
        if raw_meta:
            try:
                m = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
                current_model_id = m.get("model_job_id") or m.get("model_id")
            except Exception:
                pass

        selected_idx = 0
        if voice_models:
            for idx, vm in enumerate(voice_models):
                self.model_combo.addItem(f"🎤 {vm['name']}", vm["id"])
                if current_model_id and int(vm["id"]) == int(current_model_id):
                    selected_idx = idx
            self.model_combo.addItem("✨ 默认使用最新训练音色", None)
        else:
            self.model_combo.addItem("✨ 默认系统音色", None)

        self.model_combo.setCurrentIndex(selected_idx)
        layout.addWidget(self.model_combo)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_cancel = QPushButton("取消")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #f8fafc;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("开始重新生成")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        btn_ok.clicked.connect(self.accept)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def selected_model_job_id(self) -> int | None:
        return self.model_combo.currentData()

    def selected_model_name(self) -> str:
        return self.model_combo.currentText()


def apply_task_patches():
    # -1. Terminate any orphan/zombie client processes holding UDP 29630
    try:
        import psutil
        import subprocess
        my_pid = os.getpid()
        for p in psutil.process_iter(['pid', 'name']):
            try:
                pid = p.info['pid']
                if pid == my_pid:
                    continue
                # 1. Kill any process that is holding UDP port 29630
                is_holding_port = False
                try:
                    for conn in p.net_connections(kind='udp'):
                        if conn.laddr and conn.laddr.port == 29630:
                            is_holding_port = True
                            break
                except Exception:
                    pass

                # 2. Check if it is an older aising_client
                is_client = False
                try:
                    cmd = ' '.join(p.cmdline() or [])
                    if 'aising_client' in cmd and p.info['name'] in ('python.exe', 'pythonw.exe'):
                        is_client = True
                except Exception:
                    pass

                if is_holding_port or is_client:
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
    except Exception:
        pass

    # 0. Global Network Redirection
    try:
        import re
        import requests
        import os

        def rewrite_remote_url(url: str) -> str:
            if not isinstance(url, str):
                return url
            target_base = os.getenv("AIS_CLIENT_API_BASE_URL", "http://127.0.0.1:8200").strip().rstrip("/")
            if "ai-sing-1.oss-cn-beijing.aliyuncs.com" in url:
                url = re.sub(
                    r"https?://ai-sing-1\.oss-cn-beijing\.aliyuncs\.com/(?:api/oss/local-files/)?",
                    f"{target_base}/api/oss/local-files/",
                    url,
                )
            if "154.8.173.242" in url:
                url = re.sub(
                    r"https?://154\.8\.173\.242(?::\d+)?(?:/sing-api)?",
                    target_base,
                    url,
                )
            if "igiggle.cn" in url:
                url = re.sub(
                    r"https?://[^/]*igiggle\.cn(?::\d+)?(?:/sing-api)?",
                    target_base,
                    url,
                )
            return url

        orig_request = requests.request
        orig_session_request = requests.Session.request

        def patched_request(method, url, *args, **kwargs):
            return orig_request(method, rewrite_remote_url(url), *args, **kwargs)

        def patched_session_request(self, method, url, *args, **kwargs):
            return orig_session_request(self, method, rewrite_remote_url(url), *args, **kwargs)

        requests.request = patched_request
        requests.Session.request = patched_session_request

        try:
            from aising_client.component_cache import ClientComponentCache
            orig_ccc_init = ClientComponentCache.__init__

            def patched_ccc_init(self, catalog_url=None, root_dir=None, bundle_root=None):
                target_base = os.getenv("AIS_CLIENT_API_BASE_URL", "http://127.0.0.1:8200").strip().rstrip("/")
                if not catalog_url or "154.8.173.242" in str(catalog_url) or "igiggle.cn" in str(catalog_url):
                    catalog_url = f"{target_base}/api/public/client-components"
                orig_ccc_init(self, catalog_url=catalog_url, root_dir=root_dir, bundle_root=bundle_root)

            ClientComponentCache.__init__ = patched_ccc_init
        except Exception:
            pass
    except Exception:
        pass

    # 0.1 Expiry Bypass & Login Resilience
    try:
        from aising_client.ui.login import LoginWidget
        LoginWidget.user_expired = lambda self, user: False
        LoginWidget.saved_login_expired = lambda self: False
    except Exception:
        pass

    # 0.2 AppSettingsDialog patch for Qingxuan
    try:
        from aising_client.ui.jobs import AppSettingsDialog
        orig_app_settings_init = AppSettingsDialog.__init__

        def patched_app_settings_init(self, *args, **kwargs):
            orig_app_settings_init(self, *args, **kwargs)
            try:
                self.setWindowTitle("青玄设置")
                title_lbl = self.findChild(QLabel, "SettingsTitle")
                if title_lbl:
                    title_lbl.setText("青玄设置")
                if hasattr(self, "data_directory_path") and self.data_directory_path:
                    txt = self.data_directory_path.text()
                    if "Miaochang" in txt or "miaochang" in txt:
                        new_txt = txt.replace("Miaochang", "Qingxuan").replace("miaochang", "qingxuan")
                        self.data_directory_path.setText(new_txt)
                        self.data_directory_path.setToolTip(new_txt)
                for lbl in self.findChildren(QLabel):
                    if "妙唱" in lbl.text():
                        lbl.setText(lbl.text().replace("妙唱", "青玄"))
            except Exception:
                pass

        AppSettingsDialog.__init__ = patched_app_settings_init
    except Exception:
        pass

    # Patch ApiClient.create_song_process_job to inject voice model and local mode
    try:
        from aising_client.api import ApiClient
        orig_create_song_process_job = ApiClient.create_song_process_job

        def patched_create_song_process_job(self, path, lyrics_path, task_name, processing_options=None, pitch_analysis=None):
            if processing_options is None:
                opts = {}
            elif isinstance(processing_options, dict):
                opts = dict(processing_options)
            elif hasattr(processing_options, "to_dict"):
                opts = processing_options.to_dict()
            else:
                opts = dict(processing_options)

            # Inject selected voice model id
            model_id = getattr(self, "selected_model_job_id", None)
            if model_id:
                opts["model_job_id"] = model_id

            # Inject processing mode / is_local
            mode = getattr(self, "current_processing_mode", "remote")
            opts["processing_mode"] = mode
            opts["is_local"] = (mode == "local")

            return orig_create_song_process_job(
                self,
                path=path,
                lyrics_path=lyrics_path,
                task_name=task_name,
                processing_options=opts,
                pitch_analysis=pitch_analysis,
            )

        ApiClient.create_song_process_job = patched_create_song_process_job
    except Exception as exc:
        logger.warning("Failed to patch ApiClient.create_song_process_job: %s", exc)

    # 1. Patch TasksPage and SongUploadDialog
    try:
        from aising_client.ui.jobs import TasksPage, JobsWidget, SongUploadDialog
    except Exception as exc:
        logger.warning("Failed to import TasksPage/JobsWidget/SongUploadDialog for patch: %s", exc)
        return

    # Patch SongUploadDialog to add voice model selection dropdown
    orig_song_upload_init = SongUploadDialog.__init__

    def patched_song_upload_init(self, parent=None, *args, **kwargs):
        orig_song_upload_init(self, parent, *args, **kwargs)
        try:
            self.voice_combo = QComboBox()
            self.voice_combo.setObjectName("VoiceModelCombo")
            self.voice_combo.setStyleSheet("""
                QComboBox {
                    background-color: #0f172a;
                    color: #f8fafc;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-size: 12px;
                    min-height: 26px;
                }
                QComboBox:hover {
                    border-color: #3b82f6;
                }
                QComboBox QAbstractItemView {
                    background-color: #0f172a;
                    color: #f8fafc;
                    selection-background-color: #2563eb;
                    selection-color: #ffffff;
                }
            """)

            api = getattr(parent, "api", None)
            jobs = getattr(parent, "jobs", None)
            voice_models = get_user_voice_models(api, jobs)

            if voice_models:
                for vm in voice_models:
                    self.voice_combo.addItem(f"🎤 {vm['name']}", vm["id"])
                self.voice_combo.addItem("✨ 默认使用最新训练音色", None)
            else:
                self.voice_combo.addItem("✨ 默认系统音色", None)

            if hasattr(self, "process_mode_combo"):
                has_local = False
                for i in range(self.process_mode_combo.count()):
                    if self.process_mode_combo.itemData(i) == "local":
                        has_local = True
                        break
                if not has_local:
                    self.process_mode_combo.insertItem(0, "本地处理（不消耗积分）", "local")

            form = self.content_widget.findChild(QFormLayout)
            if form:
                form.addRow("合成音色", self.voice_combo)
        except Exception as exc:
            logger.exception("Failed to inject voice model combo into SongUploadDialog: %s", exc)

    def song_upload_selected_model_job_id(self) -> int | None:
        if hasattr(self, "voice_combo"):
            return self.voice_combo.currentData()
        return None

    SongUploadDialog.__init__ = patched_song_upload_init
    SongUploadDialog.selected_model_job_id = song_upload_selected_model_job_id

    # Patch TasksPage
    orig_tasks_init = TasksPage.__init__
    orig_render_jobs = TasksPage.render_jobs
    orig_status_label = TasksPage.status_label_for_job
    orig_upload_song = TasksPage.upload_song

    # Safe fallback for local song processor
    try:
        orig_clsp = TasksPage.create_local_song_processor

        def safe_clsp(self):
            try:
                return orig_clsp(self)
            except Exception as e:
                logger.info("Local song processor unavailable (%s), operating in server/cloud mode.", e)
                return None

        TasksPage.create_local_song_processor = safe_clsp
    except Exception as e:
        logger.warning("Failed to patch create_local_song_processor: %s", e)

    # Safe wrapper for MainWindow.show_app
    try:
        from aising_client.ui.main_window import MainWindow
        orig_show_app = MainWindow.show_app

        def patched_show_app(self, user):
            try:
                orig_show_app(self, user)
            except Exception as e:
                logger.exception("Error in show_app: %s", e)
                import traceback
                traceback.print_exc()

        MainWindow.show_app = patched_show_app
    except Exception:
        pass

    def patched_tasks_init(self, *args, **kwargs):
        orig_tasks_init(self, *args, **kwargs)
        try:
            if hasattr(self, "action_table"):
                self.action_table.setFixedWidth(160)
                self.action_table.setColumnWidth(0, 156)
                self.action_table.setHorizontalHeaderLabels(["操作"])
        except Exception as e:
            logger.warning("Error adjusting action_table width: %s", e)

    def patched_status_label(self, job):
        try:
            status = str(job.get("status", "")).lower()
            if status == "paused":
                return "已暂停"
            if status == "cancelled":
                return "已取消"
        except Exception:
            pass
        return orig_status_label(self, job)

    def handle_pause(page, job_id: int):
        try:
            page.api.pause_job(job_id)
            if hasattr(page, "set_status"):
                page.set_status(f"任务 #{job_id} 已暂停")
            if hasattr(page, "on_refresh") and callable(page.on_refresh):
                page.on_refresh()
        except Exception as exc:
            QMessageBox.warning(page, "暂停失败", str(exc))

    def handle_resume(page, job_id: int):
        try:
            page.api.resume_job(job_id)
            if hasattr(page, "set_status"):
                page.set_status(f"任务 #{job_id} 已恢复排队")
            if hasattr(page, "on_refresh") and callable(page.on_refresh):
                page.on_refresh()
        except Exception as exc:
            QMessageBox.warning(page, "恢复失败", str(exc))

    def handle_regenerate(page, job: dict):
        try:
            job_id = int(job.get("id", 0))
            task_title = page.task_name_for_job(job) if hasattr(page, "task_name_for_job") else str(job_id)
            if not task_title:
                task_title = f"任务 #{job_id}"

            voice_models = get_user_voice_models(page.api, getattr(page, "jobs", None))
            dialog = RegenerateDialog(page, job, voice_models, task_title)
            if dialog.exec() != QDialog.Accepted:
                return

            selected_model_id = dialog.selected_model_job_id()
            selected_model_name = dialog.selected_model_name()

            page.api.regenerate_job(job_id, model_job_id=selected_model_id)
            if hasattr(page, "set_status"):
                page.set_status(f"歌曲「{task_title}」已提交重新生成（{selected_model_name}），正在排队处理...")
            if hasattr(page, "on_refresh") and callable(page.on_refresh):
                page.on_refresh()
            QMessageBox.information(
                page,
                "提交成功",
                f"歌曲「{task_title}」已提交重新生成！\n合成音色：{selected_model_name}\n系统正在排队处理。",
            )
        except Exception as exc:
            QMessageBox.warning(page, "重新生成失败", str(exc))

    def handle_toggle_hide(page, job: dict):
        try:
            task_title = page.task_name_for_job(job) if hasattr(page, "task_name_for_job") else str(job.get("id", ""))
            if not task_title:
                task_title = f"任务 #{job.get('id')}"

            is_hidden_now = toggle_song_hidden(page.api, job)
            status_text = f"歌曲「{task_title}」已隐藏（播放界面不显示）" if is_hidden_now else f"歌曲「{task_title}」已恢复显示"
            if hasattr(page, "set_status"):
                page.set_status(status_text)
            if hasattr(page, "on_refresh") and callable(page.on_refresh):
                page.on_refresh()
        except Exception as exc:
            QMessageBox.warning(page, "隐藏切换失败", str(exc))

    def handle_delete(page, job: dict):
        try:
            job_id = int(job.get("id", 0))
            task_title = page.task_name_for_job(job) if hasattr(page, "task_name_for_job") else str(job_id)
            if not task_title:
                task_title = f"任务 #{job_id}"

            reply = QMessageBox.question(
                page,
                "确认删除",
                f"确定要删除任务「{task_title}」及其相关音频文件吗？\n删除后不可恢复。",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            if hasattr(page, "is_local_job") and page.is_local_job(job):
                if hasattr(page, "local_song_library"):
                    page.local_song_library.delete_song(job_id)
            else:
                page.api.delete_job(job_id)

            if hasattr(page, "set_status"):
                page.set_status(f"任务「{task_title}」已成功删除")
            if hasattr(page, "on_refresh") and callable(page.on_refresh):
                page.on_refresh()
        except Exception as exc:
            QMessageBox.warning(page, "删除失败", str(exc))

    def patched_render_jobs(self, *args, **kwargs):
        orig_render_jobs(self, *args, **kwargs)
        try:
            if hasattr(self, "action_table"):
                self.action_table.setFixedWidth(160)
                self.action_table.setColumnWidth(0, 156)
                self.action_table.setHorizontalHeaderLabels(["操作"])

            all_jobs = list(getattr(self, "local_pending_jobs", [])) + list(getattr(self, "jobs", []))
            sorted_list = self.sorted_jobs(all_jobs) if hasattr(self, "sorted_jobs") else all_jobs

            is_dark = False
            try:
                is_dark = self.table.palette().base().color().lightness() < 128
            except Exception:
                pass

            btn_style_transparent = (
                "QPushButton { background: transparent; background-color: transparent; border: none; padding: 0px; margin: 0px; }"
                "QPushButton:hover { background-color: rgba(128, 128, 128, 0.15); border-radius: 4px; }"
                "QPushButton:pressed { background-color: rgba(128, 128, 128, 0.25); }"
            )

            icon_regen = make_monochrome_icon(SVG_REGEN, is_dark=is_dark, size=18)
            icon_eye = make_monochrome_icon(SVG_EYE, is_dark=is_dark, size=18)
            icon_eye_off = make_monochrome_icon(SVG_EYE_OFF, is_dark=is_dark, size=18)
            icon_trash = make_monochrome_icon(SVG_TRASH, is_dark=is_dark, size=18)
            icon_pause = make_monochrome_icon(SVG_PAUSE, is_dark=is_dark, size=18)
            icon_play = make_monochrome_icon(SVG_PLAY, is_dark=is_dark, size=18)

            for row, job in enumerate(sorted_list):
                status = str(job.get("status", "")).lower()
                job_type = str(job.get("type", "")).lower()
                job_id = int(job.get("id", 0))

                container = QWidget()
                container.setStyleSheet("background: transparent; border: none;")
                layout = QHBoxLayout(container)
                layout.setContentsMargins(4, 2, 4, 2)
                layout.setSpacing(8)
                layout.setAlignment(Qt.AlignCenter)

                # 1. 重新生成 (极简无背景矢量图标)
                btn_regen = QPushButton()
                btn_regen.setIcon(icon_regen)
                btn_regen.setIconSize(QSize(18, 18))
                btn_regen.setToolTip("重新生成（选择音色合成）")
                btn_regen.setFixedSize(26, 26)
                btn_regen.setCursor(Qt.PointingHandCursor)
                btn_regen.setStyleSheet(btn_style_transparent)
                btn_regen.clicked.connect(lambda _, j=job: handle_regenerate(self, j))
                layout.addWidget(btn_regen)

                # 2. 隐藏 / 显示 (极简无背景矢量图标)
                song_is_hidden = is_song_hidden(job)
                btn_hide = QPushButton()
                btn_hide.setIcon(icon_eye_off if song_is_hidden else icon_eye)
                btn_hide.setIconSize(QSize(18, 18))
                btn_hide.setToolTip("取消隐藏（恢复在播放界面显示）" if song_is_hidden else "隐藏该歌曲（播放界面不显示）")
                btn_hide.setFixedSize(26, 26)
                btn_hide.setCursor(Qt.PointingHandCursor)
                btn_hide.setStyleSheet(btn_style_transparent)
                btn_hide.clicked.connect(lambda _, j=job: handle_toggle_hide(self, j))
                layout.addWidget(btn_hide)

                # 3. 删除 (极简无背景矢量图标)
                btn_delete = QPushButton()
                btn_delete.setIcon(icon_trash)
                btn_delete.setIconSize(QSize(18, 18))
                btn_delete.setToolTip("删除任务及相关音频文件")
                btn_delete.setFixedSize(26, 26)
                btn_delete.setCursor(Qt.PointingHandCursor)
                btn_delete.setStyleSheet(btn_style_transparent)
                btn_delete.clicked.connect(lambda _, j=job: handle_delete(self, j))
                layout.addWidget(btn_delete)

                # Extra for running or paused jobs: 暂停 / 恢复
                is_pausable = bool(job.get("is_pausable", status in ("queued", "running")))
                is_resumable = bool(job.get("is_resumable", status == "paused"))
                if is_pausable:
                    btn_pause = QPushButton()
                    btn_pause.setIcon(icon_pause)
                    btn_pause.setIconSize(QSize(18, 18))
                    btn_pause.setToolTip("暂停该任务执行")
                    btn_pause.setFixedSize(26, 26)
                    btn_pause.setCursor(Qt.PointingHandCursor)
                    btn_pause.setStyleSheet(btn_style_transparent)
                    btn_pause.clicked.connect(lambda _, jid=job_id: handle_pause(self, jid))
                    layout.insertWidget(0, btn_pause)
                elif is_resumable:
                    btn_resume = QPushButton()
                    btn_resume.setIcon(icon_play)
                    btn_resume.setIconSize(QSize(18, 18))
                    btn_resume.setToolTip("恢复该任务排队执行")
                    btn_resume.setFixedSize(26, 26)
                    btn_resume.setCursor(Qt.PointingHandCursor)
                    btn_resume.setStyleSheet(btn_style_transparent)
                    btn_resume.clicked.connect(lambda _, jid=job_id: handle_resume(self, jid))
                    layout.insertWidget(0, btn_resume)

                self.action_table.setCellWidget(row, 0, container)
        except Exception as exc:
            logger.exception("Failed to inject controls into table: %s", exc)

    orig_pitch_analysis_enabled = TasksPage.pitch_analysis_enabled

    def patched_pitch_analysis_enabled(self):
        if getattr(self, "song_processor", None) is None:
            return False
        try:
            return orig_pitch_analysis_enabled(self)
        except Exception:
            return False

    def patched_upload_song(self):
        try:
            lyrics_cache = getattr(self, "user_data_dir", Path(".")) / "lyrics_cache"
            supports_local = getattr(getattr(self, "edition", None), "supports_local_inference", True)
            try:
                dialog = SongUploadDialog(
                    self,
                    lyrics_cache_dir=lyrics_cache,
                    local_processing_enabled=supports_local,
                )
            except Exception:
                dialog = SongUploadDialog(self)

            if dialog.exec() != QDialog.Accepted:
                self.set_status("已取消上传")
                return

            vals = dialog.values()
            path, lyrics_path, task_name = vals[0], vals[1], vals[2]
            processing_mode = vals[3] if len(vals) > 3 else "local"

            # Pass selected voice model to api
            if hasattr(dialog, "selected_model_job_id"):
                selected_model = dialog.selected_model_job_id()
                if hasattr(self, "api"):
                    self.api.selected_model_job_id = selected_model

            if hasattr(self, "api"):
                self.api.current_processing_mode = processing_mode

            if not self.pitch_analysis_enabled():
                self.submit_song_processing(path, lyrics_path, task_name, processing_mode)
            else:
                self.start_pitch_analysis(path, lyrics_path, task_name, processing_mode)
        except Exception as exc:
            logger.exception("Error in patched upload_song: %s", exc)
            QMessageBox.warning(self, "提交失败", f"提交歌曲处理时发生错误：\n{exc}")

    def patched_submit_song_processing(self, song_path, lyrics_path, task_name, processing_mode="remote", processing_options=None, pitch_analysis=None):
        options = self.apply_song_processing_settings(processing_options)
        is_local_mode = (processing_mode == "local")

        if is_local_mode:
            # 本地处理：跳过积分扣除弹窗确认
            if hasattr(self, "set_status"):
                self.set_status(f"正在准备处理「{task_name}」（本地模式，不消耗积分）...")
        else:
            # 在线处理：按原逻辑检查免费额度或积分
            if not self.confirm_online_song_process():
                return

        if hasattr(self, "api"):
            self.api.current_processing_mode = processing_mode

        self.start_upload_task(
            "song_process",
            song_path=Path(song_path) if song_path else None,
            lyrics_path=Path(lyrics_path) if lyrics_path else None,
            task_name=task_name,
            processing_options=options,
            pitch_analysis=pitch_analysis,
            local_processing=False,
        )

    TasksPage.__init__ = patched_tasks_init
    TasksPage.pitch_analysis_enabled = patched_pitch_analysis_enabled
    TasksPage.status_label_for_job = patched_status_label
    TasksPage.render_jobs = patched_render_jobs
    TasksPage.upload_song = patched_upload_song
    TasksPage.submit_song_processing = patched_submit_song_processing

    # 2. Patch JobsWidget.refresh_jobs to populate both local songs and cloud songs in playback
    def patched_refresh_jobs(self):
        try:
            jobs = self.api.list_jobs()
            try:
                cloud_local = self.api.list_local_songs()
                if isinstance(cloud_local, list):
                    self.local_song_library.merge_cloud_library({"songs": cloud_local, "categories": []})
                elif isinstance(cloud_local, dict):
                    self.local_song_library.merge_cloud_library(cloud_local)
            except Exception:
                pass

            local_songs = self.local_song_library.list_songs()
            all_list = jobs + local_songs
            self.tasks.set_jobs(all_list)

            # Sync hidden songs
            settings = QSettings("Qingxuan", "HiddenSongs")
            raw_list = settings.value("hidden_ids", [])
            hidden_set = set(str(x) for x in (raw_list if isinstance(raw_list, list) else []))
            for j in all_list:
                meta = j.get("metadata_json")
                if meta:
                    try:
                        m = json.loads(meta) if isinstance(meta, str) else meta
                        if isinstance(m, dict) and m.get("hidden") is True:
                            hidden_set.add(str(j.get("id")))
                    except Exception:
                        pass

            seen_ids = set()
            all_song_jobs = []
            for s in local_songs:
                if s.get("type") == "song_process" and s.get("status") == "success":
                    if not is_song_hidden(s):
                        all_song_jobs.append(s)
                    seen_ids.add(s.get("id"))
            for j in jobs:
                if j.get("type") == "song_process" and j.get("status") == "success":
                    if j.get("id") not in seen_ids:
                        if not is_song_hidden(j):
                            all_song_jobs.append(j)
                        seen_ids.add(j.get("id"))

            self.playback.set_jobs(all_song_jobs)
            self.update_refresh_timer(jobs)
        except Exception as exc:
            if hasattr(self, "tasks") and hasattr(self.tasks, "set_status"):
                self.tasks.set_status(f"刷新失败: {exc}")
            self.update_refresh_timer([])

    JobsWidget.refresh_jobs = patched_refresh_jobs

    # 3. Patch PlaybackWidget (Add voice selection dialog when regenerating, and filter hidden songs)
    try:
        from aising_client.ui.playback import PlaybackWidget
    except Exception as exc:
        logger.warning("Failed to import PlaybackWidget for patch: %s", exc)
        return

    orig_playback_init = PlaybackWidget.__init__
    orig_playback_set_jobs = PlaybackWidget.set_jobs
    orig_make_song_row = PlaybackWidget.make_song_row

    def patched_playback_set_jobs(self, jobs: list[dict]):
        visible_jobs = [j for j in jobs if not is_song_hidden(j)]
        orig_playback_set_jobs(self, visible_jobs)

    def playback_trigger_regen(widget, target_job=None):
        job = target_job or widget.current_job()
        if not job:
            QMessageBox.information(widget, "提示", "请先在左侧歌曲列表中选择一首歌曲。")
            return
        job_id = int(job.get("id", 0))
        task_title = widget.song_task_label(job) if hasattr(widget, "song_task_label") else str(job_id)
        if not task_title:
            task_title = f"任务 #{job_id}"

        voice_models = get_user_voice_models(widget.api, getattr(widget, "jobs", None))
        dialog = RegenerateDialog(widget, job, voice_models, task_title)
        if dialog.exec() != QDialog.Accepted:
            return

        selected_model_id = dialog.selected_model_job_id()
        selected_model_name = dialog.selected_model_name()

        try:
            widget.api.regenerate_job(job_id, model_job_id=selected_model_id)
            if hasattr(widget, "status") and hasattr(widget.status, "setText"):
                widget.status.setText(f"歌曲「{task_title}」已提交重新生成（{selected_model_name}）")
            QMessageBox.information(
                widget,
                "成功",
                f"歌曲「{task_title}」已提交重新生成！\n合成音色：{selected_model_name}\n正在排队处理！",
            )
            parent = widget.parent()
            while parent:
                if hasattr(parent, "refresh_jobs"):
                    parent.refresh_jobs()
                    break
                parent = parent.parent()
        except Exception as exc:
            QMessageBox.warning(widget, "重新生成失败", str(exc))

    # Note: Regenerate buttons are removed from PlaybackWidget as requested (both bottom bar and song rows)
    PlaybackWidget.set_jobs = patched_playback_set_jobs
    logger.info("All task, song list, minimal buttons, and network patches applied successfully.")
