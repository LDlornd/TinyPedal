"""为现有 Windows 构建补充分发预设、离线教程、源码和卸载清单。"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tinypedal.setting.default_api import API_DEFAULT
from tinypedal.setting.default_common import COMMON_DEFAULT
from tinypedal.setting.default_module import MODULE_DEFAULT
from tinypedal.setting.default_widget import WIDGET_DEFAULT


def write_preset(payload: Path) -> None:
    """从项目默认值生成公开预设，不读取个人 settings。"""
    preset = copy.deepcopy({**COMMON_DEFAULT, **API_DEFAULT, **MODULE_DEFAULT, **WIDGET_DEFAULT})
    preset["preset"]["api_name"] = "Live for Speed"
    enabled_widgets = {"track_map", "radar", "deltabest", "deltabest_extended", "pedal"}
    enabled_modules = {"module_mapping", "module_delta", "module_vehicles", "module_relative"}
    for name in WIDGET_DEFAULT:
        preset[name]["enable"] = name in enabled_widgets
    for name in MODULE_DEFAULT:
        preset[name]["enable"] = name in enabled_modules
    positions = {"track_map": (30, 40), "radar": (430, 40), "deltabest": (30, 410),
                 "deltabest_extended": (30, 490), "pedal": (430, 410)}
    for name, (x, y) in positions.items():
        preset[name].update(position_x=x, position_y=y)
    preset["overlay"]["fixed_position"] = False
    preset["pedal"].update(show_ffb_meter=False, show_brake_pressure=False)
    preset["track_map"]["show_vehicle_class_standings"] = False
    destination = payload / "settings" / "default.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(preset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_tutorial(draft: Path, payload: Path) -> None:
    """同一份飞书草稿转换为离线 HTML，保留步骤和代码段。"""
    content = draft.read_text(encoding="utf-8")
    document = ET.fromstring("<article>" + content + "</article>")
    for element in document.iter():
        element.attrib.pop("seq", None)
        if element.tag == "title":
            element.tag = "h1"
        elif re.fullmatch(r"h[1-6]", element.tag):
            element.tag = f"h{min(int(element.tag[1]) + 1, 6)}"
    body = ET.tostring(document, encoding="unicode", method="html")
    page = """<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TinyPedal LFS 中文版使用教程</title><style>
body{font:16px/1.8 'Microsoft YaHei',sans-serif;color:#202630;background:#f4f6f8;margin:0}
article{max-width:920px;margin:32px auto;background:white;padding:40px;box-sizing:border-box}
h1,h2,h3{line-height:1.4;margin-top:1.5em}pre{background:#eef2f6;padding:18px;overflow:auto;line-height:1.5}
table{border-collapse:collapse;width:100%;margin:18px 0}td,th{border:1px solid #d7dee6;padding:10px;text-align:left}
th{background:#eef2f6}li{margin:8px 0}a{color:#1766b5}@media(max-width:700px){article{margin:0;padding:22px}}
</style>""" + body + "</html>\n"
    (payload / "使用教程.html").write_text(page, encoding="utf-8")
    shutil.copyfile(draft, payload / "docs" / "lfs-使用教程.xml")
    shutil.copyfile(ROOT / "docs" / "lfs.zh-CN.md", payload / "docs" / "lfs.zh-CN.md")
    shutil.copyfile(ROOT / "README.zh-CN.md", payload / "README.zh-CN.md")


def write_source_archive(payload: Path, release_tag: str) -> None:
    """只收集源码目录，排除凭据、虚拟环境、个人数据及子模块 Git 元数据。"""
    source_dir = payload / "source"
    source_dir.mkdir(exist_ok=True)
    source_files = [ROOT / name for name in
                    ("run.py", "build_win.py", "build_lfs.ps1", "requirements.txt", "LICENSE.txt",
                     "README.md", "README.zh-CN.md", "CONTRIBUTING.md", ".gitmodules", ".gitignore")]
    for name in ("tinypedal", "docs", "images", "thirdparty", "packaging", "tests"):
        source_files.extend(path for path in (ROOT / name).rglob("*") if path.is_file()
                            and not any(part in {".git", "__pycache__", ".pytest_cache"}
                                        for part in path.relative_to(ROOT).parts)
                            and path.suffix not in {".pyc", ".log"})
    with zipfile.ZipFile(source_dir / f"TinyPedal-LFS-{release_tag}-source.zip", "w",
                         compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(source_files)):
            archive.write(path, "TinyPedal-LFS-source/" + path.relative_to(ROOT).as_posix())
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    information = {
        "release": release_tag, "upstream_version": "2.53.2-dev", "platform": "windows-x64",
        "base_revision": revision, "source_includes_local_changes": True,
        "python": sys.version.split()[0], "builder": "py2exe 0.13.0.2",
        "validated_widgets_by_distributor": ["track_map", "radar", "deltabest", "deltabest_extended", "pedal"],
        "personal_data_included": False,
    }
    (payload / "release-info.json").write_text(json.dumps(information, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")


def write_uninstall_manifest(payload: Path, output: Path) -> None:
    """卸载只删除分发文件；不递归删除用户目录。"""
    commands = []
    for path in sorted(payload.rglob("*")):
        if path.is_file() and path.relative_to(payload).parts[0] != "settings":
            relative = str(path.relative_to(payload)).replace("$", "$$")
            commands.append(f'Delete "$INSTDIR\\{relative}"')
    directories = sorted((path for path in payload.rglob("*") if path.is_dir()),
                         key=lambda path: len(path.parts), reverse=True)
    for directory in directories:
        if directory.relative_to(payload).parts[0] != "settings":
            relative = str(directory.relative_to(payload)).replace("$", "$$")
            commands.append(f'RMDir "$INSTDIR\\{relative}"')
    output.write_text("\n".join(commands) + "\n", encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--draft", required=True)
    arguments = parser.parse_args()
    release_dir = (ROOT / arguments.release_dir).resolve()
    if release_dir.parent != ROOT or re.fullmatch(r"dist-lfs-[0-9]{8}(?:-[a-z0-9]+)?", release_dir.name) is None:
        raise ValueError("Release directory must be a dist-lfs-YYYYMMDD folder inside this repository")
    payload = release_dir / "TinyPedal"
    if not (payload / "tinypedal.exe").is_file():
        raise FileNotFoundError("Build tinypedal.exe with build_win.py before preparing the release")
    write_preset(payload)
    write_tutorial((ROOT / arguments.draft).resolve(), payload)
    write_source_archive(payload, arguments.release_tag)
    write_uninstall_manifest(payload, release_dir / "uninstall-files.nsh")
    print(f"Prepared release: {release_dir}")


if __name__ == "__main__":
    main()
