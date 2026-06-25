"""config.json 简单读写测试。"""
from webapp import paths


def test_save_then_load(tmp_path):
    paths.set_data_dir(tmp_path)
    try:
        paths.save_config({"theme": "dark", "debug": True})
        cfg = paths.load_config()
        assert cfg == {"theme": "dark", "debug": True}
    finally:
        paths.set_data_dir(None)


def test_load_missing_returns_empty(tmp_path):
    paths.set_data_dir(tmp_path)
    try:
        assert paths.load_config() == {}
    finally:
        paths.set_data_dir(None)
