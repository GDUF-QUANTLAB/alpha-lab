"""
BlazeStore配置模块测试
"""

import tempfile
from pathlib import Path

from blazestore import config


def test_get_settings_creates_config():
    """测试配置文件自动创建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_config_path = config.CONFIG_PATH
        config.CONFIG_PATH = Path(tmpdir) / "config.toml"

        try:
            settings = config.get_settings()

            assert config.CONFIG_PATH.exists()
            assert settings is not None
            assert settings.get("paths.store") is not None
        finally:
            config.CONFIG_PATH = original_config_path


def test_get_settings_existing_config():
    """测试读取已存在的配置文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_config_path = config.CONFIG_PATH
        config.CONFIG_PATH = Path(tmpdir) / "config.toml"

        try:
            config_path = config.CONFIG_PATH
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text('[paths]\nstore="/custom/path"\n')

            settings = config.get_settings()

            assert settings.get("paths.store") == "/custom/path"
        finally:
            config.CONFIG_PATH = original_config_path


def test_default_store_path():
    """测试默认存储路径"""
    assert config.DEFAULT_STORE_PATH == config.USERHOME / "BlazeStore"


def test_config_path():
    """测试配置文件路径"""
    assert config.CONFIG_PATH == config.USERHOME / ".blaze" / "config.toml"


def test_userhome():
    """测试用户家目录"""
    assert config.USERHOME.expanduser().exists()
