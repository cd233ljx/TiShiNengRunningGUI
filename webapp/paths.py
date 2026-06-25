"""数据/资源路径解析。

便携式布局：所有可写数据放在 exe 同目录（冻结模式）或项目根（开发模式）。
前端静态资源在冻结模式下从 PyInstaller `_MEIPASS` 临时解压目录读取。
"""
import sys
from pathlib import Path
from typing import Optional

_OVERRIDE_DATA_DIR: Optional[Path] = None


def set_data_dir(path: Optional[Path]) -> None:
    """测试或外部代码用：临时覆盖 data_dir 返回值。传 None 复位。"""
    global _OVERRIDE_DATA_DIR
    _OVERRIDE_DATA_DIR = path


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """开发模式下的仓库根目录 = paths.py 文件向上两级（webapp/ 的父目录）。"""
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """可写数据根目录。冻结 → exe 同目录；开发 → 项目根。"""
    if _OVERRIDE_DATA_DIR is not None:
        return _OVERRIDE_DATA_DIR
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return project_root()


def db_path() -> Path:
    """SQLite 文件路径。"""
    return data_dir() / "tsn_data.db"


def face_images_dir() -> Path:
    """人脸图片目录，自动创建。"""
    p = data_dir() / "face_images"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    """日志目录，自动创建。"""
    p = data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    """前端/后端共享的 config.json。"""
    return data_dir() / "config.json"


def frontend_dir() -> Path:
    """前端静态资源目录。冻结 → _MEIPASS/frontend；开发 → 项目根/frontend。"""
    if _is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "frontend"
    return project_root() / "frontend"


import json


def load_config() -> dict:
    p = config_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(data: dict) -> None:
    config_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
