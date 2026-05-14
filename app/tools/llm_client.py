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
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "qwen-plus-2025-07-28")


def _resolve_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY")


@dataclass(slots=True)
class OpenAICompatibleLLMClient:
    """Minimal OpenAI-compatible chat client with JSON helper methods."""

    api_key: str | None = field(default_factory=_resolve_api_key)
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: int = 120

    def chat_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        data = self._post(payload)
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected LLM response payload: {data}") from exc

    def chat_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        text = self.chat_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        parsed = self._extract_json_object(text)
        if not isinstance(parsed, dict):
            raise RuntimeError(f"Expected JSON object from LLM but received: {text}")
        return parsed

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError(
                "LLM API key is not configured. "
                "Please set OPENAI_API_KEY or DASHSCOPE_API_KEY in the environment."
            )
        endpoint = self.base_url.rstrip("/") + "/chat/completions"
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
                f"LLM request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LLM returned non-JSON payload: {raw}") from exc

    def _extract_json_object(self, text: str) -> Any:
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                stripped = "\n".join(lines[1:-1]).strip()
                if stripped.lower().startswith("json"):
                    stripped = stripped[4:].strip()

        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

        start = stripped.find("{")
        if start == -1:
            raise RuntimeError(f"Unable to extract JSON object from LLM text: {text}")

        decoder = json.JSONDecoder()
        try:
            parsed, _ = decoder.raw_decode(stripped[start:])
            return parsed
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Unable to decode JSON object from LLM text: {text}") from exc
