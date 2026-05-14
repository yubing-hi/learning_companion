from __future__ import annotations

from collections.abc import Sequence

from app.repositories.kb_repo import KnowledgeBaseRepository


class LocalKnowledgeRetriever:
    """Compatibility wrapper around the agent-facing local RAG retriever."""

    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        top_k: int = 4,
        *,
        mode: str = "qa",
        token_budget: int = 900,
        use_llm_rerank: bool = True,
    ) -> None:
        self.repository = repository
        self.top_k = top_k
        self.mode = mode
        self.token_budget = token_budget
        self.use_llm_rerank = use_llm_rerank

    def __call__(self, query: str) -> Sequence[str]:
        return self.repository.retrieve(
            query,
            top_k=self.top_k,
            mode=self.mode,
            token_budget=self.token_budget,
            use_llm_rerank=self.use_llm_rerank,
        )
