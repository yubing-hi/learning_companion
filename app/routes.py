from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.profile_models import StudentProfile
from app.models.request_models import (
    ExerciseEvaluateRequest,
    ExerciseGenerateRequest,
    InitProfileRequest,
    PlanGenerateRequest,
    UserRequest,
)
from app.models.response_models import UnifiedResponse
from app.orchestrator import LearningAssistantOrchestrator, build_orchestrator

router = APIRouter()
orchestrator: LearningAssistantOrchestrator = build_orchestrator()


@router.post("/chat", response_model=UnifiedResponse)
def chat(request: UserRequest) -> UnifiedResponse:
    return _guarded(lambda: orchestrator.handle(request))


@router.post("/exercise/generate", response_model=UnifiedResponse)
def generate_exercise(request: ExerciseGenerateRequest) -> UnifiedResponse:
    return _guarded(lambda: orchestrator.generate_exercises(request))


@router.post("/exercise/evaluate", response_model=UnifiedResponse)
def evaluate_exercise(request: ExerciseEvaluateRequest) -> UnifiedResponse:
    return _guarded(lambda: orchestrator.evaluate_exercise(request))


@router.post("/plan/generate", response_model=UnifiedResponse)
def generate_plan(request: PlanGenerateRequest) -> UnifiedResponse:
    return _guarded(lambda: orchestrator.generate_plan(request))


@router.get("/profile/{student_id}", response_model=StudentProfile)
def get_profile(student_id: str) -> StudentProfile:
    return _guarded(lambda: orchestrator.get_profile(student_id))


@router.post("/profile/init", response_model=StudentProfile)
def init_profile(request: InitProfileRequest) -> StudentProfile:
    return _guarded(lambda: orchestrator.init_profile(request))


def _guarded(callback):
    try:
        return callback()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
