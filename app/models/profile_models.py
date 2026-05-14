from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WrongQuestionRecord(BaseModel):
    question_id: str = Field(..., description="题目 ID")
    knowledge_point: str = Field(..., description="所属知识点")
    error_type: str = Field(..., description="错误类型，如概念混淆、理解错误")


class LearningHistory(BaseModel):
    recent_questions: list[str] = Field(
        default_factory=list,
        description="近期提问内容",
    )
    recent_topics: list[str] = Field(
        default_factory=list,
        description="近期涉及的知识点",
    )


class StudentProfile(BaseModel):
    student_id: str = Field(..., description="学生唯一标识")
    target: str = Field(..., description="学习目标")
    available_time: str = Field(..., description="可投入学习时间")
    knowledge_state: dict[str, str] = Field(
        default_factory=dict,
        description="各知识点掌握状态",
    )
    accuracy_by_topic: dict[str, float] = Field(
        default_factory=dict,
        description="各知识点正确率",
    )
    wrong_questions: list[WrongQuestionRecord] = Field(
        default_factory=list,
        description="错题记录",
    )
    history: LearningHistory = Field(
        default_factory=LearningHistory,
        description="近期学习历史",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds"),
        description="最近更新时间",
    )
