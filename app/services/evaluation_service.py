from __future__ import annotations

from app.models.exercise_models import EvaluationResult, ExerciseItem
from app.tools.llm_client import OpenAICompatibleLLMClient


class EvaluationService:
    """负责题目判定与反馈生成。"""

    def __init__(self, llm_client: OpenAICompatibleLLMClient | None = None) -> None:
        self.llm_client = llm_client

    def evaluate(
        self,
        exercise: ExerciseItem,
        student_answer: str,
    ) -> EvaluationResult:
        if exercise.question_type == "choice":
            return self.evaluate_choice(exercise, student_answer)
        return self.evaluate_short_answer(exercise, student_answer)

    def evaluate_choice(
        self,
        exercise: ExerciseItem,
        student_answer: str,
    ) -> EvaluationResult:
        normalized_answer = student_answer.strip().upper()
        correct_answer = exercise.answer.strip().upper()
        correct = normalized_answer == correct_answer

        feedback = (
            "回答正确，你已经掌握了这道题考查的基本概念。"
            if correct
            else f"回答错误，正确答案是 {exercise.answer}。{exercise.analysis}"
        )
        suggestion = (
            "可以继续挑战更高难度题目。"
            if correct
            else f"建议回顾“{exercise.knowledge_point}”的基本定义与典型特征。"
        )

        return EvaluationResult(
            question_id=exercise.question_id,
            correct=correct,
            score=1.0 if correct else 0.0,
            error_type=None if correct else "概念混淆",
            feedback=feedback,
            suggestion=suggestion,
            knowledge_point=exercise.knowledge_point,
        )

    def evaluate_short_answer(
        self,
        exercise: ExerciseItem,
        student_answer: str,
    ) -> EvaluationResult:
        if self.llm_client is not None:
            payload = self.llm_client.chat_json(
                system_prompt=(
                    "你是数据结构课程判题助手。"
                    "请只输出 JSON 对象，格式为 "
                    "{\"correct\": true/false, \"score\": 0到1之间数字, "
                    "\"error_type\": \"错误类型或null\", \"feedback\": \"...\", "
                    "\"suggestion\": \"...\"}。"
                ),
                user_prompt=(
                    f"知识点：{exercise.knowledge_point}\n"
                    f"题目：{exercise.question}\n"
                    f"标准答案：{exercise.answer}\n"
                    f"题目解析：{exercise.analysis}\n"
                    f"学生答案：{student_answer}\n"
                    "请判断学生答案是否正确，并给出反馈与改进建议。"
                ),
                temperature=0.1,
            )
            correct = bool(payload.get("correct", False))
            raw_score = payload.get("score", 1.0 if correct else 0.4)
            try:
                score = max(0.0, min(1.0, float(raw_score)))
            except (TypeError, ValueError):
                score = 1.0 if correct else 0.4
            error_type = str(payload.get("error_type", "")).strip()
            if not error_type or error_type.lower() == "null":
                error_type = "要点缺失"
            return EvaluationResult(
                question_id=exercise.question_id,
                correct=correct,
                score=score,
                error_type=None if correct else error_type,
                feedback=str(payload.get("feedback", "")).strip() or "已完成评估。",
                suggestion=str(payload.get("suggestion", "")).strip() or "建议回顾相关知识点。",
                knowledge_point=exercise.knowledge_point,
            )

        correct = self._keyword_match(exercise.answer, student_answer)
        feedback = (
            "回答覆盖了核心要点，整体较为完整。"
            if correct
            else "回答没有覆盖题目的核心要点，解释还不够完整。"
        )
        suggestion = (
            "可以进一步补充更规范的术语表述。"
            if correct
            else f"建议围绕“{exercise.knowledge_point}”补充定义、特征和应用场景。"
        )

        return EvaluationResult(
            question_id=exercise.question_id,
            correct=correct,
            score=1.0 if correct else 0.5,
            error_type=None if correct else "要点缺失",
            feedback=feedback,
            suggestion=suggestion,
            knowledge_point=exercise.knowledge_point,
        )

    def _keyword_match(self, reference_answer: str, student_answer: str) -> bool:
        keywords = [word for word in reference_answer.replace("，", " ").replace("。", " ").split() if word]
        if not keywords:
            return len(student_answer.strip()) > 0
        hit_count = sum(1 for keyword in keywords[:3] if keyword in student_answer)
        return hit_count >= 1
