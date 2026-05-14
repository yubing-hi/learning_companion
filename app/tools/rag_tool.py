from __future__ import annotations

from collections.abc import Sequence

from app.repositories.kb_repo import KnowledgeBaseRepository


class KnowledgeRAGTool:
    """Agent-facing tool for retrieving course knowledge snippets."""

    name = "knowledge_rag_search"
    description = "Search the local data-structure knowledge base and return prompt-ready context."

    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        *,
        mode: str = "qa",
        top_k: int = 4,
        token_budget: int = 900,
        use_llm_rerank: bool = True,
    ) -> None:
        self.repository = repository
        self.mode = mode
        self.top_k = top_k
        self.token_budget = token_budget
        self.use_llm_rerank = use_llm_rerank

    def __call__(
        self,
        query: str,
        *,
        mode: str | None = None,
        top_k: int | None = None,
        token_budget: int | None = None,
        use_llm_rerank: bool | None = None,
    ) -> str:
        documents = self.search(
            query,
            mode=mode,
            top_k=top_k,
            token_budget=token_budget,
            use_llm_rerank=use_llm_rerank,
        )
        return "\n\n".join(documents)

    def search(
        self,
        query: str,
        *,
        mode: str | None = None,
        top_k: int | None = None,
        token_budget: int | None = None,
        use_llm_rerank: bool | None = None,
    ) -> Sequence[str]:
        return self.repository.retrieve(
            query,
            mode=mode or self.mode,
            top_k=top_k or self.top_k,
            token_budget=token_budget or self.token_budget,
            use_llm_rerank=self.use_llm_rerank if use_llm_rerank is None else use_llm_rerank,
        )
