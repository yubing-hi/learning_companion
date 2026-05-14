from __future__ import annotations

import json
from pathlib import Path

from app.models.exercise_models import ExerciseItem


class QuestionRepository:
    """Load question bank files from disk and store generated questions locally."""

    def __init__(
        self,
        base_dir: str | Path = "data/question_bank",
        generated_filename: str = "_generated_questions.json",
    ) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.generated_path = self.base_dir / generated_filename

    def search(
        self,
        knowledge_point: str,
        difficulty: str,
        question_type: str,
    ) -> list[ExerciseItem]:
        matched: list[ExerciseItem] = []
        for item in self._load_all_questions():
            if item.knowledge_point != knowledge_point:
                continue
            if difficulty and item.difficulty != difficulty:
                continue
            if question_type and item.question_type != question_type:
                continue
            matched.append(item)
        return matched

    def get_by_id(self, question_id: str) -> ExerciseItem:
        for item in self._load_all_questions():
            if item.question_id == question_id:
                return item
        raise FileNotFoundError(f"Question not found for question_id={question_id}")

    def save_generated(self, items: list[ExerciseItem]) -> None:
        existing = self._load_generated_payload()
        existing.extend(item.model_dump() for item in items)
        self.generated_path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_all_questions(self) -> list[ExerciseItem]:
        questions: list[ExerciseItem] = []
        for path in sorted(self.base_dir.glob("*.json")):
            questions.extend(self._load_from_file(path))
        return questions

    def _load_from_file(self, path: Path) -> list[ExerciseItem]:
        raw_text = path.read_text(encoding="utf-8").strip()
        if not raw_text:
            return []

        raw_payload = json.loads(raw_text)
        if isinstance(raw_payload, dict):
            raw_items = raw_payload.get("questions", [])
        else:
            raw_items = raw_payload

        return [ExerciseItem.model_validate(item) for item in raw_items]

    def _load_generated_payload(self) -> list[dict]:
        if not self.generated_path.exists():
            return []

        raw_text = self.generated_path.read_text(encoding="utf-8").strip()
        if not raw_text:
            return []
        return json.loads(raw_text)
