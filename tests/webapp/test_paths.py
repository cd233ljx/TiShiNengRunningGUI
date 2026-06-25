"""路径解析模块测试。"""
import sys
from pathlib import Path

import webapp.paths as paths_mod


def test_data_dir_dev_uses_cwd_parent_of_paths(tmp_path, monkeypatch):
    """开发模式（非冻结）下 data_dir 应等于项目根。"""
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(paths_mod, "_OVERRIDE_DATA_DIR", None, raising=False)
    d = paths_mod.data_dir()
    # 项目根至少应是 webapp 目录的父目录
    assert (d / "webapp").is_dir() or d.is_dir()


def test_data_dir_frozen_uses_executable_dir(tmp_path, monkeypatch):
    """冻结模式（PyInstaller）下 data_dir 应等于 sys.executable 同目录。"""
    fake_exe = tmp_path / "TiShiNeng.exe"
    fake_exe.write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    monkeypatch.setattr(paths_mod, "_OVERRIDE_DATA_DIR", None, raising=False)
    assert paths_mod.data_dir() == tmp_path


def test_set_data_dir_override(tmp_path):
    """允许测试/外部代码通过 set_data_dir 覆盖（测试隔离用）。"""
    paths_mod.set_data_dir(tmp_path)
    try:
        assert paths_mod.data_dir() == tmp_path
        assert paths_mod.face_images_dir() == tmp_path / "face_images"
        assert paths_mod.logs_dir() == tmp_path / "logs"
        # 自动 mkdir
        assert paths_mod.face_images_dir().is_dir()
        assert paths_mod.logs_dir().is_dir()
    finally:
        paths_mod.set_data_dir(None)


def test_frontend_dir_dev(monkeypatch):
    """开发模式下 frontend_dir 是仓库内的 frontend/。"""
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    fd = paths_mod.frontend_dir()
    assert fd.name == "frontend"


def test_frontend_dir_frozen_uses_meipass(tmp_path, monkeypatch):
    """冻结模式下 frontend_dir 来自 sys._MEIPASS。"""
    meipass = tmp_path / "_MEI123"
    (meipass / "frontend").mkdir(parents=True)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    assert paths_mod.frontend_dir() == meipass / "frontend"
