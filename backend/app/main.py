"""FastAPI 应用入口。

启动：``cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000``
（Windows 上不要加 ``--reload``：reload 模式会强制 SelectorEventLoop，导致判题沙箱的 asyncio subprocess 报 NotImplementedError。）
交互式文档：http://127.0.0.1:8000/docs

部署方式
--------
- 生产：Nginx 托管前端静态资源，并把 ``/api``（及 ``/ws``）反向代理到本服务；
  业务接口统一挂在前缀 ``/api/v1`` 下，Nginx 只需转发 ``/api`` 即可覆盖全部接口。
- 开发：直接运行本服务（或经 Vite 代理），浏览器访问 http://127.0.0.1:8000/docs 调试。
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import chapters, labs
from .core.config import get_settings
from .schemas import HealthResponse

settings = get_settings()

# OpenAPI 文档元数据：控制 Swagger UI 中接口的分组与展示顺序。
tags_metadata = [
    {
        "name": "health",
        "description": "服务健康检查与存活探针。",
    },
    {
        "name": "chapters",
        "description": "章节目录与单章概览（知识点标题、Lab / 练习简表）。",
    },
    {
        "name": "labs",
        "description": "章节下的 Lab 详情（Wireshark 实验 / Socket 练习）与在线判题。",
    },
]

app = FastAPI(
    title=settings.app_name,
    description="课程章节目录、Lab（Wireshark / Socket）与在线判题接口。",
    version=settings.version,
    openapi_tags=tags_metadata,
    # 公网部署可设 ENABLE_DOCS=false 关掉交互式文档与 schema，减少可探测面。
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

app.include_router(chapters.router)
app.include_router(labs.router)

# 挂载静态资源：抓包文件 / 初始代码 / PDF 文档等，统一放在 backend/static/ 下
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get(
    "/",
    tags=["health"],
    response_model=HealthResponse,
    summary="健康检查",
    response_description="返回服务名与固定状态 ok。",
)
def root() -> HealthResponse:
    """存活探针：用于负载均衡 / 开发环境快速确认服务是否在线。"""
    return HealthResponse(status="ok", app=settings.app_name)
