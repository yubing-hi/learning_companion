from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from uuid import uuid4

from app.models.exercise_models import ExerciseItem
from app.models.profile_models import StudentProfile
from app.tools.llm_client import OpenAICompatibleLLMClient


class ExerciseService:
    """Generate exercises from LLM or local fallback sources."""

    def __init__(
        self,
        question_fetcher: Callable[[str, str, str], Sequence[ExerciseItem]] | None = None,
        llm_client: OpenAICompatibleLLMClient | None = None,
    ) -> None:
        self.question_fetcher = question_fetcher
        self.llm_client = llm_client

    def generate(
        self,
        profile: StudentProfile,
        knowledge_point: str | None = None,
        question_type: str = "choice",
        difficulty: str = "easy",
        count: int = 1,
    ) -> list[ExerciseItem]:
        target_point = knowledge_point or self._select_target_topic(profile)
        if self.llm_client is not None:
            return [
                self._generate_question(
                    knowledge_point=target_point,
                    question_type=question_type,
                    difficulty=difficulty,
                )
                for _ in range(count)
            ]

        questions = (
            list(self.question_fetcher(target_point, difficulty, question_type))
            if self.question_fetcher
            else []
        )
        if len(questions) >= count:
            return questions[:count]

        generated = list(questions)
        while len(generated) < count:
            generated.append(
                self._generate_question(
                    knowledge_point=target_point,
                    question_type=question_type,
                    difficulty=difficulty,
                )
            )
        return generated

    def _select_target_topic(self, profile: StudentProfile) -> str:
        for topic, state in profile.knowledge_state.items():
            if state == "薄弱":
                return topic
        return next(iter(profile.knowledge_state.keys()), "栈")

    def _generate_question(
        self,
        *,
        knowledge_point: str,
        question_type: str,
        difficulty: str,
    ) -> ExerciseItem:
        if self.llm_client is not None:
            payload = self.llm_client.chat_json(
                system_prompt=(
                    "你是数据结构课程的出题助手。"
                    "请只输出一个 JSON 对象，必须包含字段：question, options, answer, analysis。"
                    "如果是简答题，options 输出 null。"
                ),
                user_prompt=(
                    f"知识点：{knowledge_point}\n"
                    f"题型：{question_type}\n"
                    f"难度：{difficulty}\n"
                    "请生成一道适合大学《数据结构》课程的练习题。"
                    "如果是选择题，请提供 4 个选项。"
                    "每个选项只写选项内容，不要带 A./B./C./D. 这样的前缀。"
                    "标准答案只用 A/B/C/D 表示。"
                ),
                temperature=0.6,
            )

            normalized_type = "short_answer" if question_type == "short_answer" else "choice"
            options = self._normalize_options(payload.get("options"))
            if normalized_type == "choice" and not isinstance(options, list):
                options = ["选项一", "选项二", "选项三", "选项四"]
            if normalized_type == "short_answer":
                options = None

            return ExerciseItem(
                question_id=f"generated_{uuid4().hex[:8]}",
                knowledge_point=knowledge_point,
                question_type=normalized_type,
                difficulty=difficulty,
                question=str(payload.get("question", "")).strip(),
                options=options,
                answer=str(payload.get("answer", "")).strip(),
                analysis=str(payload.get("analysis", "")).strip(),
            )

        question_id = f"generated_{uuid4().hex[:8]}"
        if question_type == "short_answer":
            return ExerciseItem(
                question_id=question_id,
                knowledge_point=knowledge_point,
                question_type="short_answer",
                difficulty=difficulty,
                question=f"请简要说明“{knowledge_point}”的核心概念，并给出一个典型应用场景。",
                options=None,
                answer=f"{knowledge_point} 的回答应包含定义、特征和应用场景。",
                analysis=f"本题考查学生对“{knowledge_point}”的概念理解与表达能力。",
            )

        return ExerciseItem(
            question_id=question_id,
            knowledge_point=knowledge_point,
            question_type="choice",
            difficulty=difficulty,
            question=f"以下哪一项最符合“{knowledge_point}”的典型特征？",
            options=["选项一", "选项二", "选项三", "选项四"],
            answer="A",
            analysis=f"本题用于检测学生对“{knowledge_point}”基本概念的掌握情况。",
        )

    def _normalize_options(self, options: object) -> list[str] | None:
        if not isinstance(options, list):
            return None

        normalized: list[str] = []
        for option in options:
            text = str(option).strip()
            text = re.sub(r"^[A-Da-d][\.\)\:\：、\s]+", "", text).strip()
            normalized.append(text)
        return normalized
