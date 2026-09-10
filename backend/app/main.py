"""FastAPI 应用入口。

启动：``cd backend && uvicorn app.main:app --reload``
交互式文档：http://127.0.0.1:8000/docs
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import chapters, labs
from .core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="课程章节目录、Lab（Wireshark / Socket）与在线判题接口。",
    version=settings.version,
)

app.include_router(chapters.router)
app.include_router(labs.router)

# 挂载静态资源：抓包文件 / 初始代码 / PDF 文档等，统一放在 backend/static/ 下
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["health"], summary="健康检查")
def root() -> dict[str, str]:
    """简单的存活探针。"""
    return {"status": "ok", "app": settings.app_name}
