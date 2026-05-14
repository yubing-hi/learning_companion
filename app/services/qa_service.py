from __future__ import annotations

from collections.abc import Callable, Sequence

from app.models.profile_models import StudentProfile
from app.models.response_models import QAResponse
from app.tools.llm_client import OpenAICompatibleLLMClient


class QAService:
    """负责课程问答与基于 RAG 的回答生成。"""

    def __init__(
        self,
        retriever: Callable[[str], Sequence[str]] | None = None,
        llm_client: OpenAICompatibleLLMClient | None = None,
    ) -> None:
        self.retriever = retriever
        self.llm_client = llm_client

    def answer(self, question: str, profile: StudentProfile) -> QAResponse:
        documents = list(self._retrieve_context(question))
        knowledge_points = self._extract_knowledge_points(question, profile, documents)
        student_level = self._resolve_student_level(knowledge_points, profile)
        answer = self._generate_answer(
            question=question,
            documents=documents,
            knowledge_points=knowledge_points,
            student_level=student_level,
        )

        return QAResponse(
            answer=answer,
            knowledge_points=knowledge_points,
            sources=self._build_sources(documents),
            profile_update_needed=bool(knowledge_points),
        )

    def _retrieve_context(self, question: str) -> Sequence[str]:
        if self.retriever is None:
            return []
        return self.retriever(question)

    def _extract_knowledge_points(
        self,
        question: str,
        profile: StudentProfile,
        documents: Sequence[str],
    ) -> list[str]:
        if self.llm_client is None:
            text = question.lower()
            return [
                point
                for point in profile.knowledge_state.keys()
                if point.lower() in text
            ]

        known_topics = sorted(profile.knowledge_state.keys())
        context = "\n\n".join(documents[:3]) if documents else "无"
        payload = self.llm_client.chat_json(
            system_prompt=(
                "你是数据结构课程助教。"
                "请从学生问题和检索上下文中抽取最相关的知识点。"
                "只输出 JSON 对象，格式为 {\"knowledge_points\": [\"知识点1\", ...]}。"
            ),
            user_prompt=(
                f"候选知识点：{known_topics}\n"
                f"学生问题：{question}\n"
                f"检索上下文：\n{context}\n"
                "如果问题明显涉及候选外的重要知识点，也可以补充，但不要输出解释。"
            ),
        )
        raw_points = payload.get("knowledge_points", [])
        if not isinstance(raw_points, list):
            return []
        points = [str(point).strip() for point in raw_points if str(point).strip()]
        return list(dict.fromkeys(points))

    def _resolve_student_level(
        self,
        knowledge_points: list[str],
        profile: StudentProfile,
    ) -> str:
        if not knowledge_points:
            return "一般"

        priorities = {"薄弱": 0, "一般": 1, "掌握良好": 2}
        states = [profile.knowledge_state.get(point, "一般") for point in knowledge_points]
        return min(states, key=lambda state: priorities.get(state, 1))

    def _build_prompt(
        self,
        *,
        question: str,
        documents: Sequence[str],
        knowledge_points: list[str],
        student_level: str,
    ) -> str:
        context = "\n\n".join(documents) if documents else "无额外检索内容"
        points = "、".join(knowledge_points) if knowledge_points else "未明确识别"
        return (
            "你是数据结构课程的学伴智能体。\n"
            f"学生水平：{student_level}\n"
            f"涉及知识点：{points}\n"
            f"学生问题：{question}\n"
            f"参考资料：\n{context}\n"
            "要求：优先依据参考资料作答；资料不足时再结合通用课程知识补充。"
            "回答结构请使用“定义-原理-示例-易错点”。"
        )

    def _generate_answer(
        self,
        *,
        question: str,
        documents: Sequence[str],
        knowledge_points: list[str],
        student_level: str,
    ) -> str:
        if self.llm_client is not None:
            return self.llm_client.chat_text(
                system_prompt="你是一个严谨、友好、面向学生的数据结构课程智能学伴。",
                user_prompt=self._build_prompt(
                    question=question,
                    documents=documents,
                    knowledge_points=knowledge_points,
                    student_level=student_level,
                ),
                temperature=0.3,
            )

        point_text = "、".join(knowledge_points) if knowledge_points else "相关数据结构知识点"
        detail = (
            "我会展开解释基础概念，并补充示例和易错点。"
            if student_level == "薄弱"
            else "我会给出简洁总结，并补充关键原理。"
        )
        context_hint = f"参考资料数：{len(documents)}" if documents else "当前未命中外部资料"
        return (
            f"定义：下面围绕{point_text}回答你的问题“{question}”。\n"
            f"原理：{detail}\n"
            "示例：可以结合顺序结构与链式结构、先进先出与后进先出等典型场景理解。\n"
            "易错点：注意不要混淆概念定义、操作特征和适用场景。\n"
            f"补充说明：{context_hint}。"
        )

    def _build_sources(self, documents: Sequence[str]) -> list[str]:
        sources: list[str] = []
        for idx, document in enumerate(documents, start=1):
            lines = document.splitlines()
            first_line = lines[0].strip() if lines else ""
            if first_line.startswith("SOURCE:"):
                sources.append(first_line.removeprefix("SOURCE:").strip())
            else:
                sources.append(f"retrieved_doc_{idx}")
        return sources
