from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import sys

PLUGIN_BUNDLE_NAME = "QXuanAI.vst3"
OBSOLETE_BUNDLE_NAMES = ["MiaoChang.vst3", "QingXuan.vst3"]


class PluginInstallError(RuntimeError):
    pass


@dataclass
class PluginInstallResult:
    installed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def message(self) -> str:
        parts = []
        if self.installed:
            parts.append("已安装/覆盖: " + "、".join(self.installed))
        if self.skipped:
            parts.append("已跳过: " + "、".join(self.skipped))
        return "；".join(parts) if parts else "机架插件状态未变更"


def default_plugin_source_root() -> Path:
    if getattr(sys, "_MEIPASS", None):
        meipass_vendor = Path(sys._MEIPASS) / "vendor" / "vst3"
        if meipass_vendor.exists():
            return meipass_vendor

    # 1. Inside package: aising_client/vendor/vst3
    pkg_vendor = Path(__file__).resolve().parent / "vendor" / "vst3"
    if pkg_vendor.exists():
        return pkg_vendor

    # 2. Outside package: ai-sing-client/vendor/vst3
    root_vendor = Path(__file__).resolve().parents[1] / "vendor" / "vst3"
    if root_vendor.exists():
        return root_vendor

    return pkg_vendor


class Vst3PluginInstaller:
    def __init__(
        self,
        source_root: Path | None = None,
        x64_target: Path | None = None,
        win32_target: Path | None = None,
    ) -> None:
        self.source_root = source_root or default_plugin_source_root()
        self.targets = {
            "x64": x64_target or (Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Common Files" / "VST3"),
            "Win32": win32_target or (Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Common Files" / "VST3"),
        }

    def source_plugin(self, architecture: str) -> Path:
        source = self.source_root / architecture / PLUGIN_BUNDLE_NAME
        if not source.exists():
            label = "64 位" if architecture == "x64" else "32 位"
            raise PluginInstallError(f"缺少 {label} QXuanAI.vst3 插件，请检查客户端安装包。")
        return source

    def install_all(self) -> PluginInstallResult:
        result = PluginInstallResult()
        for architecture, target_root in self.targets.items():
            source = self.source_plugin(architecture)
            target = target_root / PLUGIN_BUNDLE_NAME
            try:
                target_root.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(source, target)

                # Clean up legacy MiaoChang.vst3 and QingXuan.vst3 completely
                for legacy_name in OBSOLETE_BUNDLE_NAMES:
                    for ext in ["", ".bak"]:
                        legacy_target = target_root / f"{legacy_name}{ext}"
                        if legacy_target.exists():
                            shutil.rmtree(legacy_target, ignore_errors=True)

                result.installed.append(architecture)
            except PermissionError as exc:
                raise PluginInstallError("没有权限修改机架插件目录，请关闭正在使用插件的机架软件后重试。") from exc
            except OSError as exc:
                raise PluginInstallError(f"机架插件安装失败: {exc}") from exc
        return result
