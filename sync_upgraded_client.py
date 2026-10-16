import os
import shutil
import marshal

# 1. Source extracted directory
src_root = None
for root, dirs, files in os.walk(r"E:\miscol\AISing"):
    if "PYZ.pyz_extracted" in root and root.endswith("aising_client"):
        src_root = root
        break

if not src_root:
    raise FileNotFoundError("Could not find PYZ.pyz_extracted/aising_client")

print("Found source root:", src_root)

# 2. Destination directory in current project
dst_root = r"E:\miscol\AISing\ai-sing-client\aising_client"
print("Destination root:", dst_root)

# 3. Remove old .py source files from dst that are superseded by the upgraded 10x larger .pyc modules
superseded_py = [
    os.path.join(dst_root, "api.py"),
    os.path.join(dst_root, "ui", "jobs.py"),
    os.path.join(dst_root, "ui", "login.py"),
    os.path.join(dst_root, "ui", "main_window.py"),
    os.path.join(dst_root, "ui", "playback.py"),
    os.path.join(dst_root, "ui", "separator.py"),
    os.path.join(dst_root, "audio", "engine.py"),
    os.path.join(dst_root, "audio", "lyrics.py"),
    os.path.join(dst_root, "audio", "metadata.py"),
    os.path.join(dst_root, "audio", "meter.py"),
]

for py in superseded_py:
    if os.path.isfile(py):
        backup_py = py + ".old_git_backup"
        if not os.path.exists(backup_py):
            os.rename(py, backup_py)
            print("Backed up old git source:", py, "->", backup_py)
        else:
            os.remove(py)
            print("Removed old git source:", py)

# Clear __pycache__ in dst
for root, dirs, files in os.walk(dst_root):
    if os.path.basename(root) == "__pycache__":
        shutil.rmtree(root)

# 4. Copy all upgraded .pyc modules into dst_root
for r, d, files in os.walk(src_root):
    rel = os.path.relpath(r, src_root)
    target_dir = os.path.join(dst_root, rel) if rel != "." else dst_root
    os.makedirs(target_dir, exist_ok=True)
    for f in files:
        if f.endswith(".pyc"):
            src_file = os.path.join(r, f)
            dst_file = os.path.join(target_dir, f)
            if f == "api.pyc":
                # Patch api.pyc URL constant from cloud to local http://127.0.0.1:8200
                with open(src_file, "rb") as fp:
                    header = fp.read(16)
                    code = marshal.load(fp)
                new_consts = list(code.co_consts)
                for i, c in enumerate(new_consts):
                    if c == "https://ai-sing.igiggle.cn/sing-api":
                        new_consts[i] = "http://127.0.0.1:8200"
                        print(f"Patched api.pyc URL constant at index {i} to http://127.0.0.1:8200")
                patched_code = code.replace(co_consts=tuple(new_consts))
                with open(dst_file, "wb") as fp:
                    fp.write(header)
                    marshal.dump(patched_code, fp)
                print(f"Wrote patched {dst_file}")
            else:
                shutil.copy2(src_file, dst_file)
                print(f"Copied upgraded {f} ({os.path.getsize(dst_file)} bytes) -> {rel}")

# 5. Set edition.json in dst to "full" to unlock all features
edition_json = os.path.join(dst_root, "edition.json")
with open(edition_json, "w", encoding="utf-8") as f:
    f.write('{"edition": "full"}\n')
print("Set local edition.json to full")

# 6. Ensure main.py in ai-sing-client boots the upgraded MainWindow cleanly
main_py_content = '''import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from aising_client.api import ApiClient
from aising_client.branding import fetch_branding
from aising_client.logging_config import setup_logging
from aising_client.ui.main_window import MainWindow
from aising_client.ui.window_chrome import DarkTitleBarController, enable_windows_dark_mode


def main() -> int:
    setup_logging()
    enable_windows_dark_mode()
    app = QApplication(sys.argv)
    if hasattr(app, "styleHints") and hasattr(app.styleHints(), "setColorScheme"):
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    title_bar_controller = DarkTitleBarController(app)
    app.installEventFilter(title_bar_controller)
    branding = fetch_branding(ApiClient())
    app.setApplicationName(branding.app_name)
    app.setApplicationDisplayName(branding.display_name)
    if branding.icon_path.exists():
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(branding.icon_path)))
    window = MainWindow(branding=branding)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
'''

with open(os.path.join(dst_root, "main.py"), "w", encoding="utf-8") as f:
    f.write(main_py_content)
print("Updated main.py")

print("All upgraded modules successfully synchronized into current project!")
