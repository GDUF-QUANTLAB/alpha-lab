from pathlib import Path

from dynaconf import Dynaconf
from loguru import logger

USERHOME = Path("~").expanduser()  # 用户家目录

CONFIG_PATH = USERHOME / ".blaze" / "config.toml"
DEFALUT_STORE_PATH = USERHOME / "BlazeStore"


def get_settings():
    if CONFIG_PATH.exists():
        pass
    else:
        logger.warning(f"Config file not found, creating in {CONFIG_PATH}")
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.touch()

        # 处理路径中的反斜杠
        store_path = str(DEFALUT_STORE_PATH).replace("\\", "/")

        # 构建配置文件内容（避免 f-string 中的反斜杠）
        content = "[paths]\n"
        content += f'store="{store_path}"\n'

        CONFIG_PATH.write_text(content)
    return Dynaconf(settings_files=[CONFIG_PATH])


_settings = get_settings()
