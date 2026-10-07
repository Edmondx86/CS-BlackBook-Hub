"""章节目录与单章概览接口。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path

from ..core.config import API_PREFIX
from ..mock_data import CHAPTERS
from ..schemas import Chapter, ChapterOverview, ErrorResponse, LabBrief

router = APIRouter(prefix=API_PREFIX, tags=["chapters"])


def _to_overview(ch: Chapter) -> ChapterOverview:
    """把内部 Chapter 转成对外概览结构。"""
    return ChapterOverview(
        id=ch.id,
        number=ch.number,
        title=ch.title,
        summary=ch.summary,
        knowledge_points=[kp.title for kp in ch.knowledge_points],
        wireshark_labs=[LabBrief(id=ws.id, title=ws.title) for ws in ch.wireshark_labs],
        socket_exercises=[LabBrief(id=ex.id, title=ex.title) for ex in ch.socket_exercises],
    )


@router.get(
    "/chapters",
    response_model=list[ChapterOverview],
    summary="获取所有章节的目录与概览",
    response_description="按编号顺序返回全部章节的概览列表。",
)
def list_chapters() -> list[ChapterOverview]:
    """返回每个章节的编号、标题、知识点标题，以及 Lab / 练习的极简列表。"""
    return [_to_overview(ch) for ch in CHAPTERS]


@router.get(
    "/chapters/{chapter_id}",
    response_model=ChapterOverview,
    summary="获取指定章节的概览与实验列表",
    response_description="单个章节的概览；章节不存在时返回 404。",
    responses={404: {"model": ErrorResponse, "description": "章节不存在"}},
)
def get_chapter(
    chapter_id: Annotated[str, Path(description="章节 id，如 ch1", examples=["ch1"])],
) -> ChapterOverview:
    """按 ``chapter_id`` 返回单个章节的编号、标题、知识点与 Lab 简表。"""
    chapter = next((c for c in CHAPTERS if c.id == chapter_id), None)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter '{chapter_id}' not found")
    return _to_overview(chapter)
