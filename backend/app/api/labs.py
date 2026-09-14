"""Lab 详情与在线判题接口。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path

from ..core.config import API_PREFIX
from ..mock_data import get_lab
from ..schemas import ErrorResponse, EvaluationResult, Lab, RunRequest
from ..services.evaluator import evaluate_submission

router = APIRouter(prefix=API_PREFIX, tags=["labs"])


@router.get(
    "/chapters/{chapter_id}/labs/{lab_id}",
    response_model=Lab,
    summary="获取指定章节下某个 Lab 的详细指南与附件元数据",
    response_description="Lab 详情（含 Markdown 指南全文、初始代码、参考答案与附件元数据）。",
    responses={404: {"model": ErrorResponse, "description": "章节或 Lab 不存在"}},
)
def get_lab_detail(
    chapter_id: Annotated[str, Path(description="章节 id，如 ch2", examples=["ch2"])],
    lab_id: Annotated[str, Path(description="Lab id，如 sock-web / ws-http", examples=["sock-web"])],
) -> Lab:
    """按 ``chapter_id`` + ``lab_id`` 返回该章节下 Lab 的 Markdown 指南全文与附件元数据。"""
    lab = get_lab(chapter_id, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found in chapter '{chapter_id}'")
    return lab


@router.post(
    "/chapters/{chapter_id}/labs/{lab_id}/run",
    response_model=EvaluationResult,
    summary="运行并判题用户提交的 Socket 作业",
    response_description="判题结果：测试通过/失败、逐条校验明细与实时日志。",
    responses={
        404: {"model": ErrorResponse, "description": "章节或 Lab 不存在"},
        400: {"model": ErrorResponse, "description": "该 Lab 不支持在线判题（仅 Socket 练习支持）"},
    },
)
async def run_lab(
    chapter_id: Annotated[str, Path(description="章节 id，如 ch2", examples=["ch2"])],
    lab_id: Annotated[str, Path(description="Lab id，如 sock-web / sock-pinger", examples=["sock-web"])],
    body: RunRequest,
) -> EvaluationResult:
    """把提交源码交给判题服务：按 ``lab_id`` 分发策略，``test_cases`` 参与判定。

    返回 JSON：测试通过/失败 + 实时 stdout/stderr 日志。
    """
    lab = get_lab(chapter_id, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found in chapter '{chapter_id}'")
    if lab.type != "socket":
        raise HTTPException(status_code=400, detail="仅 Socket 编程练习支持在线判题")

    return await evaluate_submission(lab_id, body.code, lab.test_cases)
