from __future__ import annotations

import json
from pathlib import Path

from app.models.profile_models import StudentProfile


class ProfileRepository:
    """Persist student profiles as local JSON files."""

    def __init__(self, base_dir: str | Path = "data/profiles") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get(self, student_id: str) -> StudentProfile:
        path = self._path_for(student_id)
        if not path.exists():
            raise FileNotFoundError(f"Profile not found for student_id={student_id}")

        return StudentProfile.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, profile: StudentProfile) -> None:
        path = self._path_for(profile.student_id)
        path.write_text(
            json.dumps(profile.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def exists(self, student_id: str) -> bool:
        return self._path_for(student_id).exists()

    def _path_for(self, student_id: str) -> Path:
        return self.base_dir / f"{student_id}.json"
