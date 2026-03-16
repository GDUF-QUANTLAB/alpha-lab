"""
BlazeStore配置管理模块

提供配置文件管理、路径处理和配置加载功能。
"""

from __future__ import annotations

from pathlib import Path

from dynaconf import Dynaconf
from loguru import logger

USERHOME = Path("~").expanduser()
CONFIG_PATH = USERHOME / ".blaze" / "config.toml"
DEFAULT_STORE_PATH = USERHOME / "BlazeStore"


def get_settings() -> Dynaconf:
    """
    获取BlazeStore配置对象。

    该函数会检查配置文件是否存在，如果不存在则创建默认配置文件。
    配置文件路径为 ~/.blaze/config.toml

    Returns:
        Dynaconf: 配置对象，可以通过get方法获取配置值

    Examples:
        >>> settings = get_settings()
        >>> store_path = settings.get("paths.store")
        >>> print(store_path)
        /home/user/BlazeStore
    """
    if CONFIG_PATH.exists():
        pass
    else:
        logger.warning(f"Config file not found, creating in {CONFIG_PATH}")
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.touch()

        store_path = str(DEFAULT_STORE_PATH).replace("\\", "/")

        content = "[paths]\n"
        content += f'store="{store_path}"\n'

        CONFIG_PATH.write_text(content)
    return Dynaconf(settings_files=[CONFIG_PATH])


_settings = get_settings()
