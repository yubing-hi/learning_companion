from __future__ import annotations

from pydantic import BaseModel, Field


class StudyPlan(BaseModel):
    student_id: str = Field(..., description="学生唯一标识")
    duration: str = Field(..., description="学习计划周期")
    goals: list[str] = Field(
        default_factory=list,
        description="阶段性目标",
    )
    daily_plan: list[str] = Field(
        default_factory=list,
        description="按天或按阶段的计划安排",
    )
    focus_topics: list[str] = Field(
        default_factory=list,
        description="重点复习知识点",
    )
