from __future__ import annotations

from app.models.plan_models import StudyPlan
from app.models.profile_models import StudentProfile
from app.tools.llm_client import OpenAICompatibleLLMClient


class PlannerService:
    """负责根据画像生成阶段性学习计划。"""

    def __init__(self, llm_client: OpenAICompatibleLLMClient | None = None) -> None:
        self.llm_client = llm_client

    def generate_plan(
        self,
        profile: StudentProfile,
        duration: str,
    ) -> StudyPlan:
        if self.llm_client is not None:
            payload = self.llm_client.chat_json(
                system_prompt=(
                    "你是学习计划助手。"
                    "请根据学生画像生成个性化学习计划。"
                    "只输出 JSON 对象，格式为 "
                    "{\"goals\": [..], \"daily_plan\": [..], \"focus_topics\": [..]}。"
                ),
                user_prompt=(
                    f"学习周期：{duration}\n"
                    f"学生画像：\n{profile.model_dump_json(indent=2)}\n"
                    "请给出结构清晰、可执行的学习计划。"
                ),
                temperature=0.3,
            )
            return StudyPlan(
                student_id=profile.student_id,
                duration=duration,
                goals=[str(item).strip() for item in payload.get("goals", []) if str(item).strip()],
                daily_plan=[str(item).strip() for item in payload.get("daily_plan", []) if str(item).strip()],
                focus_topics=[str(item).strip() for item in payload.get("focus_topics", []) if str(item).strip()],
            )

        focus_topics = self._select_focus_topics(profile)
        goals = self._build_goals(profile, focus_topics)
        daily_plan = self._build_daily_plan(duration, focus_topics, profile.available_time)

        return StudyPlan(
            student_id=profile.student_id,
            duration=duration,
            goals=goals,
            daily_plan=daily_plan,
            focus_topics=focus_topics,
        )

    def _select_focus_topics(self, profile: StudentProfile) -> list[str]:
        weak_topics = [
            topic
            for topic, state in profile.knowledge_state.items()
            if state == "薄弱"
        ]
        if weak_topics:
            return weak_topics[:3]
        return list(profile.knowledge_state.keys())[:3]

    def _build_goals(
        self,
        profile: StudentProfile,
        focus_topics: list[str],
    ) -> list[str]:
        goals = []
        if focus_topics:
            goals.append(f"优先强化 {', '.join(focus_topics)} 相关知识点")
        goals.append(f"围绕目标“{profile.target}”安排复习节奏")
        return goals

    def _build_daily_plan(
        self,
        duration: str,
        focus_topics: list[str],
        available_time: str,
    ) -> list[str]:
        topic_count = max(1, len(focus_topics))
        if "3天" in duration:
            return [
                f"Day1：复习 {focus_topics[0]} 的定义、基本操作与典型题，预计学习 {available_time}",
                f"Day2：复习 {focus_topics[min(1, topic_count - 1)]} 并完成基础练习，预计学习 {available_time}",
                f"Day3：综合回顾 {', '.join(focus_topics)} 并完成错题复盘，预计学习 {available_time}",
            ]

        plan = []
        for index, topic in enumerate(focus_topics, start=1):
            plan.append(f"阶段{index}：集中复习 {topic}，预计学习 {available_time}")
        plan.append(f"最后阶段：综合练习与错题回顾，预计学习 {available_time}")
        return plan
