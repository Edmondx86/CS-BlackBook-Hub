"""Lab 详情与在线判题接口。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..mock_data import get_lab
from ..schemas import EvaluationResult, Lab, RunRequest
from ..services.evaluator import evaluate_submission

router = APIRouter(prefix="/api/v1", tags=["labs"])


@router.get(
    "/labs/{lab_id}",
    response_model=Lab,
    summary="获取指定 Lab 的详细 Markdown 指南与附件元数据",
)
def get_lab_detail(lab_id: str) -> Lab:
    """按 ``lab_id`` 返回 Lab 的 Markdown 指南全文与附件元数据。"""
    lab = get_lab(lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found")
    return lab


@router.post(
    "/labs/{lab_id}/run",
    response_model=EvaluationResult,
    summary="运行并判题用户提交的 Socket 作业",
)
async def run_lab(lab_id: str, body: RunRequest) -> EvaluationResult:
    """把提交源码交给判题服务：按 ``lab_id`` 分发策略，``test_cases`` 参与判定。

    返回 JSON：测试通过/失败 + 实时 stdout/stderr 日志。
    """
    lab = get_lab(lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail=f"Lab '{lab_id}' not found")
    if lab.type != "socket":
        raise HTTPException(status_code=400, detail="仅 Socket 编程练习支持在线判题")

    return await evaluate_submission(lab_id, body.code, lab.test_cases)
