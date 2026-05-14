from __future__ import annotations

import re

from app.models.profile_models import StudentProfile
from app.models.request_models import (
    ExerciseEvaluateRequest,
    ExerciseGenerateRequest,
    InitProfileRequest,
    PlanGenerateRequest,
    UserRequest,
)
from app.models.response_models import ProfileSummary, UnifiedResponse
from app.repositories.kb_repo import KnowledgeBaseRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.question_repo import QuestionRepository
from app.services.diagnosis_service import DiagnosisService
from app.services.evaluation_service import EvaluationService
from app.services.exercise_service import ExerciseService
from app.services.planner_services import PlannerService
from app.services.qa_service import QAService
from app.tools.llm_client import OpenAICompatibleLLMClient
from app.tools.retriever import LocalKnowledgeRetriever


class LearningAssistantOrchestrator:
    """Coordinate repositories and service modules into unified workflows."""

    DEFAULT_TOPICS = ("栈", "队列", "链表", "树", "二叉树", "图", "递归", "排序", "查找")

    def __init__(
        self,
        profile_repo: ProfileRepository,
        question_repo: QuestionRepository,
        kb_repo: KnowledgeBaseRepository,
        qa_service: QAService,
        diagnosis_service: DiagnosisService,
        exercise_service: ExerciseService,
        evaluation_service: EvaluationService,
        planner_service: PlannerService,
    ) -> None:
        self.profile_repo = profile_repo
        self.question_repo = question_repo
        self.kb_repo = kb_repo
        self.qa_service = qa_service
        self.diagnosis_service = diagnosis_service
        self.exercise_service = exercise_service
        self.evaluation_service = evaluation_service
        self.planner_service = planner_service

    def init_profile(self, request: InitProfileRequest) -> StudentProfile:
        if self.profile_repo.exists(request.student_id):
            return self.profile_repo.get(request.student_id)

        profile = StudentProfile(
            student_id=request.student_id,
            target=request.target,
            available_time=request.available_time,
            knowledge_state={topic: "一般" for topic in self.DEFAULT_TOPICS},
            accuracy_by_topic={topic: 0.5 for topic in self.DEFAULT_TOPICS},
        )
        self.profile_repo.save(profile)
        return profile

    def get_profile(self, student_id: str) -> StudentProfile:
        return self.profile_repo.get(student_id)

    def handle(self, request: UserRequest) -> UnifiedResponse:
        mode = request.mode or self._detect_mode(request.message)
        if mode == "qa":
            return self._handle_qa(request)
        if mode == "exercise":
            exercise_request = ExerciseGenerateRequest(
                student_id=request.student_id,
                knowledge_point=self._extract_knowledge_point(request.message, request.student_id),
                question_type=self._infer_question_type(request.message),
                difficulty=self._infer_difficulty(request.message),
                count=1,
            )
            return self.generate_exercises(exercise_request)
        if mode == "plan":
            plan_request = PlanGenerateRequest(
                student_id=request.student_id,
                duration=self._extract_duration(request.message),
            )
            return self.generate_plan(plan_request)
        raise ValueError("通过 /chat 只支持 qa、exercise、plan 模式；evaluation 请调用专门接口。")

    def generate_exercises(self, request: ExerciseGenerateRequest) -> UnifiedResponse:
        profile = self.profile_repo.get(request.student_id)
        exercises = self.exercise_service.generate(
            profile=profile,
            knowledge_point=request.knowledge_point,
            question_type=request.question_type,
            difficulty=request.difficulty,
            count=request.count,
        )
        self.question_repo.save_generated(exercises)
        return UnifiedResponse(
            type="exercise",
            data={"items": [item.model_dump() for item in exercises]},
            profile_summary=self._build_profile_summary(profile),
        )

    def evaluate_exercise(self, request: ExerciseEvaluateRequest) -> UnifiedResponse:
        profile = self.profile_repo.get(request.student_id)
        exercise = self.question_repo.get_by_id(request.question_id)
        result = self.evaluation_service.evaluate(exercise, request.student_answer)
        updated_profile = self.diagnosis_service.update_profile(
            profile=profile,
            knowledge_point=result.knowledge_point,
            evaluation_result=result,
            interaction_text=request.student_answer,
        )
        self.profile_repo.save(updated_profile)
        return UnifiedResponse(
            type="evaluation",
            data=result.model_dump(),
            profile_summary=self._build_profile_summary(updated_profile),
        )

    def generate_plan(self, request: PlanGenerateRequest) -> UnifiedResponse:
        profile = self.profile_repo.get(request.student_id)
        plan = self.planner_service.generate_plan(profile, request.duration)
        return UnifiedResponse(
            type="plan",
            data=plan.model_dump(),
            profile_summary=self._build_profile_summary(profile),
        )

    def _handle_qa(self, request: UserRequest) -> UnifiedResponse:
        profile = self.profile_repo.get(request.student_id)
        qa_response = self.qa_service.answer(request.message, profile)
        updated_profile = profile
        if qa_response.profile_update_needed:
            knowledge_point = qa_response.knowledge_points[0] if qa_response.knowledge_points else ""
            updated_profile = self.diagnosis_service.update_profile(
                profile=profile,
                knowledge_point=knowledge_point,
                interaction_text=request.message,
            )
            self.profile_repo.save(updated_profile)

        return UnifiedResponse(
            type="qa",
            data=qa_response.model_dump(),
            profile_summary=self._build_profile_summary(updated_profile),
        )

    def _build_profile_summary(self, profile: StudentProfile) -> ProfileSummary:
        return self.diagnosis_service.summarize_profile(profile)

    def _detect_mode(self, message: str) -> str:
        text = message.lower()
        if any(keyword in text for keyword in ("出一道题", "练习", "刷题", "来道题", "测试")):
            return "exercise"
        if any(keyword in text for keyword in ("计划", "规划", "复习安排", "学习安排")):
            return "plan"
        return "qa"

    def _extract_duration(self, message: str) -> str:
        match = re.search(r"(\d+\s*[天周月])", message)
        if match:
            return match.group(1).replace(" ", "")
        return "3天"

    def _infer_question_type(self, message: str) -> str:
        return "short_answer" if "简答" in message else "choice"

    def _infer_difficulty(self, message: str) -> str:
        if any(keyword in message for keyword in ("困难", "难", "进阶")):
            return "hard"
        if any(keyword in message for keyword in ("中等", "一般")):
            return "medium"
        return "easy"

    def _extract_knowledge_point(self, message: str, student_id: str) -> str | None:
        profile = self.profile_repo.get(student_id)
        ordered_topics = list(profile.knowledge_state.keys()) + [
            topic for topic in self.DEFAULT_TOPICS if topic not in profile.knowledge_state
        ]
        for topic in ordered_topics:
            if topic in message:
                return topic
        return None


def build_orchestrator() -> LearningAssistantOrchestrator:
    llm_client = OpenAICompatibleLLMClient()
    profile_repo = ProfileRepository()
    question_repo = QuestionRepository()
    kb_repo = KnowledgeBaseRepository(llm_client=llm_client)

    qa_service = QAService(
        retriever=LocalKnowledgeRetriever(
            kb_repo,
            mode="qa",
            top_k=4,
            token_budget=900,
            use_llm_rerank=True,
        ),
        llm_client=llm_client,
    )
    diagnosis_service = DiagnosisService(llm_client=llm_client)
    exercise_service = ExerciseService(
        question_fetcher=question_repo.search,
        llm_client=llm_client,
    )
    evaluation_service = EvaluationService(llm_client=llm_client)
    planner_service = PlannerService(llm_client=llm_client)

    return LearningAssistantOrchestrator(
        profile_repo=profile_repo,
        question_repo=question_repo,
        kb_repo=kb_repo,
        qa_service=qa_service,
        diagnosis_service=diagnosis_service,
        exercise_service=exercise_service,
        evaluation_service=evaluation_service,
        planner_service=planner_service,
    )
