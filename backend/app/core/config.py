"""全局配置与工具。"""

from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    """应用级配置：常量内联，运行期配置从环境变量读取。

    如需更强的类型与校验，可改用 ``pydantic-settings`` 的 ``BaseSettings``。
    """

    app_name = "计算机网络（自顶向下）学习平台后端"
    version = "1.0.0"
    api_prefix = "/api/v1"

    @property
    def host(self) -> str:
        return os.getenv("HOST", "0.0.0.0")

    @property
    def port(self) -> int:
        return int(os.getenv("PORT", "8000"))


@lru_cache
def get_settings() -> Settings:
    """返回进程内单例配置。"""
    return Settings()
