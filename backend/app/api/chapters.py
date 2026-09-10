"""章节目录与单章概览接口。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..mock_data import CHAPTERS
from ..schemas import Chapter, ChapterOverview, LabBrief

router = APIRouter(prefix="/api/v1", tags=["chapters"])


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
)
def list_chapters() -> list[ChapterOverview]:
    """返回每个章节的编号、标题、知识点标题，以及 Lab / 练习的极简列表。"""
    return [_to_overview(ch) for ch in CHAPTERS]


@router.get(
    "/chapters/{chapter_id}",
    response_model=ChapterOverview,
    summary="获取指定章节的概览与实验列表",
)
def get_chapter(chapter_id: str) -> ChapterOverview:
    """按 ``chapter_id`` 返回单个章节的编号、标题、知识点与 Lab 简表。"""
    chapter = next((c for c in CHAPTERS if c.id == chapter_id), None)
    if chapter is None:
        raise HTTPException(status_code=404, detail=f"Chapter '{chapter_id}' not found")
    return _to_overview(chapter)
