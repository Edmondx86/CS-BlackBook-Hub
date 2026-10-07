"""全局配置与工具。"""

from __future__ import annotations

import os
from functools import lru_cache

# 统一 API 前缀：所有业务路由、前端请求、Nginx 反代都以它为准（Nginx 只需把 /api 转发到本服务）。
API_PREFIX = "/api/v1"


class Settings:
    """应用级配置：常量内联，运行期开关从环境变量读取。

    如需更强的类型与校验，可改用 ``pydantic-settings`` 的 ``BaseSettings``。
    """

    app_name = "CS-BlackBook-Hub"
    version = "1.0.0"

    @property
    def enable_docs(self) -> bool:
        """是否开放 ``/docs`` 与 ``/openapi.json``。

        公网部署建议在 compose 里设 ``ENABLE_DOCS=false``，少一处可被探测/滥用的入口；
        本地开发默认开启，方便调接口。
        """
        return os.getenv("ENABLE_DOCS", "true").strip().lower() not in {"0", "false", "no", "off"}


@lru_cache
def get_settings() -> Settings:
    """返回进程内单例配置。"""
    return Settings()
