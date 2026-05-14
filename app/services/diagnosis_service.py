from __future__ import annotations

from datetime import datetime

from app.models.exercise_models import EvaluationResult
from app.models.profile_models import (
    StudentProfile,
    WrongQuestionRecord,
)
from app.models.response_models import ProfileSummary
from app.tools.llm_client import OpenAICompatibleLLMClient


class DiagnosisService:
    """负责学情诊断、画像更新与学习状况总结。"""

    def __init__(self, llm_client: OpenAICompatibleLLMClient | None = None) -> None:
        self.llm_client = llm_client

    def update_profile(
        self,
        profile: StudentProfile,
        knowledge_point: str,
        evaluation_result: EvaluationResult | None = None,
        interaction_text: str | None = None,
    ) -> StudentProfile:
        if interaction_text:
            self._update_history(profile, interaction_text, knowledge_point)

        if not knowledge_point:
            profile.updated_at = self._timestamp()
            return profile

        if evaluation_result is None:
            if self.llm_client is not None:
                payload = self.llm_client.chat_json(
                    system_prompt=(
                        "你是学习画像更新助手。"
                        "学生这次只有提问没有做题。"
                        "请根据学生画像和提问内容，对该知识点做保守更新。"
                        "只输出 JSON 对象，格式为 "
                        "{\"knowledge_state\": \"薄弱/一般/掌握良好\", \"accuracy\": 0到1之间数字}。"
                    ),
                    user_prompt=(
                        f"当前学生画像：\n{profile.model_dump_json(indent=2)}\n"
                        f"知识点：{knowledge_point}\n"
                        f"学生提问：{interaction_text or ''}\n"
                        "请进行保守更新，不要因为一次提问就大幅提高掌握状态。"
                    ),
                    temperature=0.1,
                )
                self._apply_mastery_update(profile, knowledge_point, payload)
                profile.updated_at = self._timestamp()
                return profile
            profile.knowledge_state[knowledge_point] = profile.knowledge_state.get(knowledge_point, "一般")
            profile.updated_at = self._timestamp()
            return profile

        if self.llm_client is not None:
            return self._update_profile_with_llm(
                profile=profile,
                knowledge_point=knowledge_point,
                evaluation_result=evaluation_result,
                interaction_text=interaction_text,
            )

        self._update_accuracy(profile, knowledge_point, evaluation_result.correct)
        self._update_knowledge_state(profile, knowledge_point, evaluation_result.correct)
        if not evaluation_result.correct:
            self._append_wrong_question(profile, evaluation_result)

        profile.updated_at = self._timestamp()
        return profile

    def summarize_profile(self, profile: StudentProfile) -> ProfileSummary:
        if self.llm_client is None:
            weak_topics = [
                topic for topic, state in profile.knowledge_state.items() if state == "薄弱"
            ]
            strong_topics = [
                topic for topic, state in profile.knowledge_state.items() if state == "掌握良好"
            ]
            return ProfileSummary(weak_topics=weak_topics, strong_topics=strong_topics)

        payload = self.llm_client.chat_json(
            system_prompt=(
                "你是学习画像分析助手。"
                "请根据学生画像总结当前薄弱知识点和掌握较好的知识点。"
                "判断规则：knowledge_state 为“薄弱”或 accuracy_by_topic < 0.5 可归为 weak_topics；"
                "knowledge_state 为“掌握良好”或 accuracy_by_topic >= 0.8 可归为 strong_topics；"
                "其余不要输出。"
                "只输出 JSON 对象，格式为 "
                "{\"weak_topics\": [..], \"strong_topics\": [..]}。"
            ),
            user_prompt=f"学生画像如下：\n{profile.model_dump_json(indent=2)}",
            temperature=0.1,
        )
        weak_topics = [
            str(topic).strip()
            for topic in payload.get("weak_topics", [])
            if str(topic).strip()
        ]
        strong_topics = [
            str(topic).strip()
            for topic in payload.get("strong_topics", [])
            if str(topic).strip()
        ]
        return ProfileSummary(
            weak_topics=list(dict.fromkeys(weak_topics)),
            strong_topics=list(dict.fromkeys(strong_topics)),
        )

    def _update_history(
        self,
        profile: StudentProfile,
        interaction_text: str,
        knowledge_point: str,
    ) -> None:
        profile.history.recent_questions.append(interaction_text)
        if knowledge_point:
            profile.history.recent_topics.append(knowledge_point)

        profile.history.recent_questions = profile.history.recent_questions[-10:]
        profile.history.recent_topics = profile.history.recent_topics[-10:]

    def _update_accuracy(
        self,
        profile: StudentProfile,
        knowledge_point: str,
        correct: bool,
    ) -> None:
        old_accuracy = profile.accuracy_by_topic.get(knowledge_point, 0.5)
        target = 1.0 if correct else 0.0
        profile.accuracy_by_topic[knowledge_point] = round(old_accuracy * 0.7 + target * 0.3, 2)

    def _update_knowledge_state(
        self,
        profile: StudentProfile,
        knowledge_point: str,
        correct: bool,
    ) -> None:
        current_state = profile.knowledge_state.get(knowledge_point, "一般")
        accuracy = profile.accuracy_by_topic.get(knowledge_point, 0.5)

        if not correct and accuracy < 0.5:
            profile.knowledge_state[knowledge_point] = "薄弱"
            return

        if current_state == "薄弱" and correct:
            profile.knowledge_state[knowledge_point] = "一般"
            return

        if current_state == "一般" and accuracy >= 0.8:
            profile.knowledge_state[knowledge_point] = "掌握良好"
            return

        if not correct and current_state == "掌握良好":
            profile.knowledge_state[knowledge_point] = "一般"
            return

        profile.knowledge_state[knowledge_point] = current_state

    def _append_wrong_question(
        self,
        profile: StudentProfile,
        evaluation_result: EvaluationResult,
    ) -> None:
        profile.wrong_questions.append(
            WrongQuestionRecord(
                question_id=evaluation_result.question_id,
                knowledge_point=evaluation_result.knowledge_point,
                error_type=evaluation_result.error_type or "未知错误",
            )
        )
        profile.wrong_questions = profile.wrong_questions[-20:]

    def _update_profile_with_llm(
        self,
        *,
        profile: StudentProfile,
        knowledge_point: str,
        evaluation_result: EvaluationResult,
        interaction_text: str | None,
    ) -> StudentProfile:
        payload = self.llm_client.chat_json(
            system_prompt=(
                "你是学习画像更新助手。"
                "请根据学生当前画像、最近作答和评估结果，更新指定知识点的掌握状态和正确率。"
                "只输出 JSON 对象，格式为 "
                "{\"knowledge_state\": \"薄弱/一般/掌握良好\", "
                "\"accuracy\": 0到1之间数字, "
                "\"append_wrong_question\": true/false, "
                "\"error_type\": \"错误类型或null\"}。"
            ),
            user_prompt=(
                f"当前学生画像：\n{profile.model_dump_json(indent=2)}\n"
                f"本次知识点：{knowledge_point}\n"
                f"本次评估结果：\n{evaluation_result.model_dump_json(indent=2)}\n"
                f"学生本次作答：{interaction_text or ''}\n"
                "请输出更新建议。"
            ),
            temperature=0.1,
        )

        self._apply_mastery_update(profile, knowledge_point, payload)

        if bool(payload.get("append_wrong_question", not evaluation_result.correct)) and not evaluation_result.correct:
            error_type = str(
                payload.get("error_type", evaluation_result.error_type or "未知错误")
            ).strip() or "未知错误"
            profile.wrong_questions.append(
                WrongQuestionRecord(
                    question_id=evaluation_result.question_id,
                    knowledge_point=evaluation_result.knowledge_point,
                    error_type=error_type,
                )
            )
            profile.wrong_questions = profile.wrong_questions[-20:]

        profile.updated_at = self._timestamp()
        return profile

    def _apply_mastery_update(
        self,
        profile: StudentProfile,
        knowledge_point: str,
        payload: dict,
    ) -> None:
        current_state = profile.knowledge_state.get(knowledge_point, "一般")
        state = str(payload.get("knowledge_state", current_state)).strip()
        profile.knowledge_state[knowledge_point] = state or current_state
        profile.accuracy_by_topic[knowledge_point] = round(
            self._clamped_accuracy(profile, knowledge_point, payload.get("accuracy")),
            2,
        )

    def _clamped_accuracy(
        self,
        profile: StudentProfile,
        knowledge_point: str,
        raw_accuracy: object,
    ) -> float:
        fallback = profile.accuracy_by_topic.get(knowledge_point, 0.5)
        try:
            accuracy = float(raw_accuracy)
        except (TypeError, ValueError):
            accuracy = fallback
        return max(0.0, min(1.0, accuracy))

    def _timestamp(self) -> str:
        return datetime.now().isoformat(timespec="seconds")
