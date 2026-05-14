from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request

from app.config import load_local_env


load_local_env()

DEFAULT_BASE_URL = os.getenv(
    "OPENAI_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
DEFAULT_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-v4")


def _resolve_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY")


@dataclass(slots=True)
class OpenAICompatibleEmbeddingClient:
    """Small OpenAI-compatible embeddings client used by the local RAG index."""

    api_key: str | None = field(default_factory=_resolve_api_key)
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_EMBEDDING_MODEL
    timeout: int = 120

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key:
            raise RuntimeError(
                "Embedding API key is not configured. "
                "Set OPENAI_API_KEY or DASHSCOPE_API_KEY to enable dense retrieval."
            )

        payload = {
            "model": self.model,
            "input": texts,
        }
        data = self._post(payload)
        try:
            rows = sorted(data["data"], key=lambda item: item["index"])
            return [list(map(float, row["embedding"])) for row in rows]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Unexpected embedding response payload: {data}") from exc

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = self.base_url.rstrip("/") + "/embeddings"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"Embedding request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Embedding request failed: {exc.reason}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Embedding endpoint returned non-JSON payload: {raw}") from exc
