from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExerciseItem(BaseModel):
    question_id: str = Field(..., description="题目 ID")
    knowledge_point: str = Field(..., description="所属知识点")
    question_type: Literal["choice", "short_answer"] = Field(
        ...,
        description="题目类型",
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        ...,
        description="题目难度",
    )
    question: str = Field(..., description="题干")
    options: list[str] | None = Field(
        default=None,
        description="选择题选项；简答题可为空",
    )
    answer: str = Field(..., description="标准答案")
    analysis: str = Field(..., description="题目解析")


class EvaluationResult(BaseModel):
    question_id: str = Field(..., description="题目 ID")
    correct: bool = Field(..., description="是否答对")
    score: float = Field(..., ge=0.0, le=1.0, description="题目得分")
    error_type: str | None = Field(
        default=None,
        description="错误类型",
    )
    feedback: str = Field(..., description="评估反馈")
    suggestion: str = Field(..., description="改进建议")
    knowledge_point: str = Field(..., description="对应知识点")
