from __future__ import annotations

from pydantic import BaseModel, Field


class QAResponse(BaseModel):
    answer: str = Field(..., description="结构化问答结果")
    knowledge_points: list[str] = Field(
        default_factory=list,
        description="本次问答涉及的知识点",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="引用的知识库来源",
    )
    profile_update_needed: bool = Field(
        default=False,
        description="是否建议触发画像更新",
    )


class ProfileSummary(BaseModel):
    weak_topics: list[str] = Field(
        default_factory=list,
        description="当前薄弱知识点",
    )
    strong_topics: list[str] = Field(
        default_factory=list,
        description="当前掌握较好的知识点",
    )


class UnifiedResponse(BaseModel):
    type: str = Field(..., description="响应类型，如 qa、exercise、evaluation、plan")
    data: dict = Field(..., description="具体业务数据")
    profile_summary: ProfileSummary = Field(
        default_factory=ProfileSummary,
        description="用于前端展示的画像摘要",
    )
