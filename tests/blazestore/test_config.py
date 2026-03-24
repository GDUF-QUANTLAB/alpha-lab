"""
blazestore.config 测试
"""

import tempfile
from pathlib import Path

from blazestore.config import CONFIG_PATH, DEFAULT_STORE_PATH


def test_get_settings_creates_config():
    """测试配置文件不存在时自动创建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_config_path = Path(tmpdir) / "config.toml"

        original_path = None
        try:
            import blazestore.config as config_module

            original_path = config_module.CONFIG_PATH
            config_module.CONFIG_PATH = test_config_path

            settings = config_module.get_settings()

            assert test_config_path.exists()
            assert settings.get("paths.store") is not None
        finally:
            if original_path:
                config_module.CONFIG_PATH = original_path


def test_get_settings_existing_config():
    """测试读取已存在的配置文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_config_path = Path(tmpdir) / "config.toml"
        test_config_path.write_text('[paths]\nstore="/custom/path"\n')

        original_path = None
        try:
            import blazestore.config as config_module

            original_path = config_module.CONFIG_PATH
            config_module.CONFIG_PATH = test_config_path

            settings = config_module.get_settings()

            assert settings.get("paths.store") == "/custom/path"
        finally:
            if original_path:
                config_module.CONFIG_PATH = original_path


def test_default_store_path():
    """测试默认存储路径"""
    assert DEFAULT_STORE_PATH.exists() or DEFAULT_STORE_PATH.parent.exists()
    assert "BlazeStore" in str(DEFAULT_STORE_PATH)


def test_config_path_location():
    """测试配置文件路径"""
    home = Path.home()
    assert str(CONFIG_PATH).startswith(str(home))
    assert ".blaze" in str(CONFIG_PATH)
    assert "config.toml" in str(CONFIG_PATH)
