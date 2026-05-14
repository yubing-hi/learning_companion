from __future__ import annotations

from app.repositories.kb_repo import KnowledgeBaseRepository
from app.tools.embedding_client import OpenAICompatibleEmbeddingClient


def main() -> None:
    repository = KnowledgeBaseRepository(
        embedding_client=OpenAICompatibleEmbeddingClient(),
    )
    chunks = repository.rebuild_index()
    embedded_count = sum(1 for chunk in chunks if chunk.embedding)
    print(f"Built knowledge index with {len(chunks)} chunks.")
    print(f"Embedded chunks: {embedded_count}.")


if __name__ == "__main__":
    main()
