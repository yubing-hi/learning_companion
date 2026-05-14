from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class UserRequest(BaseModel):
    student_id: str = Field(..., description="学生唯一标识")
    message: str = Field(..., min_length=1, description="用户输入的自然语言消息")
    mode: Literal["qa", "exercise", "evaluation", "plan"] | None = Field(
        default=None,
        description="可选模式；为空时由 Controller 自动判断",
    )


class InitProfileRequest(BaseModel):
    student_id: str = Field(..., description="学生唯一标识")
    target: str = Field(..., min_length=1, description="学习目标")
    available_time: str = Field(..., min_length=1, description="可投入学习时间")


class ExerciseGenerateRequest(BaseModel):
    student_id: str = Field(..., description="学生唯一标识")
    knowledge_point: str | None = Field(default=None, description="指定知识点")
    question_type: Literal["choice", "short_answer"] = Field(
        default="choice",
        description="题目类型",
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="easy",
        description="题目难度",
    )
    count: int = Field(default=1, ge=1, le=10, description="生成题目数量")


class ExerciseEvaluateRequest(BaseModel):
    student_id: str = Field(..., description="学生唯一标识")
    question_id: str = Field(..., description="题目 ID")
    student_answer: str = Field(..., min_length=1, description="学生答案")


class PlanGenerateRequest(BaseModel):
    student_id: str = Field(..., description="学生唯一标识")
    duration: str = Field(..., min_length=1, description="学习计划周期，如 3天 或 1周")
