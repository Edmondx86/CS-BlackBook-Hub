"""Pydantic 数据模型 —— 所有 API 请求/响应的严格类型定义。

设计要点
--------
1. 所有模型继承 :class:`_StrictModel`，其 ``extra="forbid"`` 使任何未声明的
   字段都会触发校验错误，满足「严格数据类型校验」的需求。
2. 使用 ``Literal`` 约束枚举类字段（Lab 类型、编程语言、附件类别）。
3. 使用 ``field_validator`` 对文件路径做后缀校验（.pcap / .md 等）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _StrictModel(BaseModel):
    """公共基类：拒绝响应/请求中任何未声明的字段。"""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------
# 内部存储模型（完整数据结构，供 mock / 数据库层使用）
# --------------------------------------------------------------------------

class KnowledgePoint(_StrictModel):
    """章节内的单个知识点。"""

    id: str = Field(..., min_length=1, description="知识点唯一标识，如 kp-1-1")
    title: str = Field(..., min_length=1, description="知识点标题")
    summary: str = Field(default="", description="一句话概述")


class TestCase(_StrictModel):
    """Socket 编程练习的单个测试用例。"""

    name: str = Field(..., min_length=1, description="用例名称")
    input: str = Field(default="", description="程序标准输入（可选）")
    expected: str = Field(..., description="期望输出")


class WiresharkLab(_StrictModel):
    """Wireshark 实验元数据（.pcap 抓包 + Markdown 指南）。"""

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    pcap_path: str = Field(..., description="抓包文件 .pcap 的相对路径")
    guide_path: str = Field(..., description="实验指南 Markdown 的相对路径")

    @field_validator("pcap_path")
    @classmethod
    def _check_pcap(cls, v: str) -> str:
        if not v.lower().endswith(".pcap"):
            raise ValueError("pcap_path 必须以 .pcap 结尾")
        return v

    @field_validator("guide_path")
    @classmethod
    def _check_guide(cls, v: str) -> str:
        if not v.lower().endswith((".md", ".markdown")):
            raise ValueError("guide_path 必须以 .md / .markdown 结尾")
        return v


class SocketExercise(_StrictModel):
    """Socket 编程练习元数据（初始代码模板 + 测试用例）。"""

    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    language: Literal["python", "c", "java"] = Field(default="python")
    starter_code_path: str = Field(..., description="初始代码模板的相对路径")
    guide_path: str = Field(..., description="练习说明 Markdown 的相对路径")
    test_cases: list[TestCase] = Field(default_factory=list)

    @field_validator("starter_code_path")
    @classmethod
    def _check_starter(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("starter_code_path 不能为空")
        return v


class Chapter(_StrictModel):
    """完整章节数据（内部存储模型）。"""

    id: str = Field(..., min_length=1)
    number: str = Field(..., description="章节编号，如 Chapter 1")
    title: str = Field(..., min_length=1)
    summary: str = Field(default="")
    knowledge_points: list[KnowledgePoint] = Field(default_factory=list)
    wireshark_labs: list[WiresharkLab] = Field(default_factory=list)
    socket_exercises: list[SocketExercise] = Field(default_factory=list)

    @field_validator("number")
    @classmethod
    def _check_number(cls, v: str) -> str:
        if not v.lower().startswith("chapter"):
            raise ValueError("章节编号需形如 'Chapter N'")
        return v


# --------------------------------------------------------------------------
# 对外响应模型（概览 / Lab 详情）
# --------------------------------------------------------------------------

class LabBrief(_StrictModel):
    """概览页中 Lab / 练习的极简信息。"""

    id: str
    title: str


class ChapterOverview(_StrictModel):
    """GET /api/v1/chapters 返回的章节概览。"""

    id: str
    number: str
    title: str
    summary: str = ""
    knowledge_points: list[str] = Field(..., description="知识点标题列表")
    wireshark_labs: list[LabBrief] = Field(default_factory=list)
    socket_exercises: list[LabBrief] = Field(default_factory=list)


class Attachment(_StrictModel):
    """Lab 详情中的附件元数据。"""

    name: str = Field(..., description="文件名")
    path: str = Field(..., description="附件相对路径")
    kind: Literal["pcap", "markdown", "code", "test"] = Field(..., description="附件类别")
    description: str = Field(default="")


class Lab(_StrictModel):
    """GET /api/v1/labs/{lab_id} 返回的 Lab 详情。

    Wireshark 实验与 Socket 练习共用此统一结构，``type`` 字段加以区分。
    """

    id: str
    chapter_id: str
    type: Literal["wireshark", "socket"]
    title: str
    summary: str = ""
    language: Literal["python", "c", "java"] | None = Field(
        default=None, description="仅 Socket 练习使用"
    )
    guide_path: str = Field(..., description="Markdown 指南的相对路径")
    guide: str = Field(..., description="Markdown 指南的完整内容")
    starter_code: str = Field(default="", description="初始代码模板内容（已内联，前端直接使用）")
    reference_code: str = Field(default="", description="参考答案代码（已内联，供「显示参考答案」使用）")
    document_path: str | None = Field(default=None, description="作业要求文档（PDF）的访问路径")
    attachments: list[Attachment] = Field(default_factory=list)
    test_cases: list[TestCase] = Field(default_factory=list)


# --------------------------------------------------------------------------
# 判题（evaluator）相关模型
# --------------------------------------------------------------------------

class RunRequest(_StrictModel):
    """POST /api/v1/labs/{lab_id}/run 的请求体。"""

    code: str = Field(..., min_length=1, description="用户提交的源码")


class EvaluationCheck(_StrictModel):
    """判题过程中单项校验的结果。"""

    name: str = Field(..., description="校验项名称，如「状态码 200」")
    passed: bool
    detail: str = Field(default="", description="校验详情")


class EvaluationResult(_StrictModel):
    """判题服务的 JSON 返回结构（通过/失败 + 实时日志）。"""

    passed: bool
    status: Literal["passed", "failed", "timeout", "error"]
    summary: str = Field(..., description="一句话结论")
    port: int = Field(..., description="本次运行使用的动态端口")
    duration_ms: int = Field(..., description="耗时（毫秒）")
    status_code: int | None = Field(default=None, description="被测服务返回的 HTTP 状态码")
    headers: dict[str, str] = Field(default_factory=dict, description="被测服务返回的响应头")
    body_preview: str = Field(default="", description="响应 Body 预览（截断）")
    checks: list[EvaluationCheck] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list, description="实时 stdout/stderr 日志")
    stdout: str = Field(default="")
    stderr: str = Field(default="")
