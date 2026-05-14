from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
import re
import time
from typing import Any

from app.tools.embedding_client import OpenAICompatibleEmbeddingClient
from app.tools.llm_client import OpenAICompatibleLLMClient


@dataclass(slots=True)
class KnowledgeChunk:
    chunk_id: str
    file_name: str
    section_title: str
    text: str
    topic: str = ""
    subtopics: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    char_count: int = 0
    prev_chunk_id: str | None = None
    next_chunk_id: str | None = None
    embedding: list[float] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> KnowledgeChunk:
        return cls(
            chunk_id=str(payload.get("chunk_id", "")),
            file_name=str(payload.get("file_name", "")),
            section_title=str(payload.get("section_title", "")),
            text=str(payload.get("text", "")),
            topic=str(payload.get("topic", "")),
            subtopics=[str(item) for item in payload.get("subtopics", [])],
            aliases=[str(item) for item in payload.get("aliases", [])],
            char_count=int(payload.get("char_count", len(str(payload.get("text", ""))))),
            prev_chunk_id=payload.get("prev_chunk_id"),
            next_chunk_id=payload.get("next_chunk_id"),
            embedding=payload.get("embedding"),
        )


@dataclass(slots=True)
class RetrievedChunk:
    chunk: KnowledgeChunk
    sparse_score: float = 0.0
    dense_score: float = 0.0
    metadata_score: float = 0.0
    recall_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0


@dataclass(slots=True)
class RetrievalConfig:
    mode: str = "qa"
    top_k_sparse: int = 8
    top_k_dense: int = 8
    merge_top_n: int = 12
    llm_rerank_top_n: int = 8
    final_top_k: int = 4
    token_budget: int = 900
    candidate_files_limit: int = 4
    use_llm_rerank: bool = True


class KnowledgeBaseRepository:
    """Indexed local RAG retriever with hybrid recall and optional LLM rerank."""

    STOP_TERMS = {
        "什么",
        "区别",
        "比较",
        "如何",
        "怎么",
        "为什么",
        "有哪些",
        "作用",
        "应用",
        "定义",
        "概念",
        "原理",
        "介绍",
        "一个",
        "the",
        "and",
        "for",
        "with",
    }

    def __init__(
        self,
        base_dir: str | Path = "data/knowledge_base",
        vector_dir: str | Path = "data/vector_store",
        chunk_size: int = 380,
        embedding_client: OpenAICompatibleEmbeddingClient | None = None,
        llm_client: OpenAICompatibleLLMClient | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.vector_dir = Path(vector_dir)
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_path = self.vector_dir / "kb_chunks.jsonl"
        self.manifest_path = self.vector_dir / "kb_manifest.json"
        self.chunk_size = chunk_size
        self.embedding_client = embedding_client or OpenAICompatibleEmbeddingClient()
        self.llm_client = llm_client
        self._chunks_cache: list[KnowledgeChunk] | None = None
        self._chunk_by_id: dict[str, KnowledgeChunk] = {}
        self._last_embedding_error = False

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        *,
        mode: str = "qa",
        token_budget: int | None = None,
        use_llm_rerank: bool | None = None,
    ) -> list[str]:
        config = self._config_for(
            mode=mode,
            top_k=top_k,
            token_budget=token_budget,
            use_llm_rerank=use_llm_rerank,
        )
        query_text = self._normalize(query)
        query_terms = self._tokenize(query)
        if not query_text or not query_terms:
            return []

        chunks = self._ensure_index()
        if not chunks:
            return []

        candidate_files = self._prefilter_files(chunks, query_text, query_terms, config)
        candidates = [chunk for chunk in chunks if chunk.file_name in candidate_files]
        if not candidates:
            candidates = chunks

        query_embedding = self._embed_query(query)
        merged = self._hybrid_recall(
            candidates=candidates,
            query_text=query_text,
            query_terms=query_terms,
            query_embedding=query_embedding,
            config=config,
        )
        if not merged:
            return []

        reranked = self._rule_rerank(merged, query_text, query_terms)
        reranked = self._llm_rerank(query, reranked, config)
        final_chunks = self._expand_and_pack(reranked, config)
        return [self._format_chunk(idx, item) for idx, item in enumerate(final_chunks, start=1)]

    def rebuild_index(self) -> list[KnowledgeChunk]:
        chunks = self._build_chunks()
        self._attach_neighbors(chunks)
        self._attach_embeddings(chunks)
        self._write_index(chunks)
        self._chunks_cache = chunks
        self._chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        return chunks

    def _config_for(
        self,
        *,
        mode: str,
        top_k: int,
        token_budget: int | None,
        use_llm_rerank: bool | None,
    ) -> RetrievalConfig:
        budgets = {
            "qa": 900,
            "exercise": 600,
            "evaluation": 600,
            "planner": 400,
        }
        final_top_k = max(1, top_k)
        return RetrievalConfig(
            mode=mode,
            final_top_k=final_top_k,
            token_budget=token_budget or budgets.get(mode, 900),
            use_llm_rerank=True if use_llm_rerank is None else use_llm_rerank,
        )

    def _ensure_index(self) -> list[KnowledgeChunk]:
        if self._chunks_cache is not None and not self._is_index_stale():
            return self._chunks_cache
        if self.chunks_path.exists() and not self._is_index_stale():
            chunks = self._read_index()
            self._chunks_cache = chunks
            self._chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
            return chunks
        return self.rebuild_index()

    def _is_index_stale(self) -> bool:
        if not self.chunks_path.exists() or not self.manifest_path.exists():
            return True
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return True
        current_files = self._source_fingerprint()
        if manifest.get("source_files") != current_files:
            return True
        if self.embedding_client.api_key and not manifest.get("embedding_enabled"):
            if not manifest.get("embedding_api_key_available"):
                return True
            if manifest.get("embedding_error"):
                return False
            return True
        if (
            manifest.get("embedding_enabled")
            and manifest.get("embedding_model") != self.embedding_client.model
        ):
            return True
        return False

    def _source_fingerprint(self) -> list[dict[str, Any]]:
        return [
            {
                "name": path.name,
                "mtime": path.stat().st_mtime,
                "size": path.stat().st_size,
            }
            for path in self._candidate_files()
        ]

    def _candidate_files(self) -> list[Path]:
        files: list[Path] = []
        for pattern in ("*.md", "*.txt"):
            files.extend(sorted(self.base_dir.rglob(pattern)))
        return [
            path
            for path in files
            if path.is_file()
            and path.name.lower() != "readme.md"
            and "summary" not in {part.lower() for part in path.parts}
        ]

    def _build_chunks(self) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        for path in self._candidate_files():
            chunks.extend(self._load_chunks_from_file(path))
        return chunks

    def _load_chunks_from_file(self, path: Path) -> list[KnowledgeChunk]:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return []

        metadata, body = self._parse_front_matter(content)
        body = body.strip()
        if not body:
            return []

        doc_title = str(metadata.get("title") or path.stem)
        topic = str(metadata.get("topic") or self._infer_topic(path))
        subtopics = self._ensure_list(metadata.get("subtopics"))
        aliases = self._ensure_list(metadata.get("aliases"))
        if doc_title not in aliases:
            aliases.append(doc_title)

        sections = self._split_content_by_headings(body, doc_title)
        chunks: list[KnowledgeChunk] = []
        for section_index, (section_title, section_text) in enumerate(sections):
            for part_index, part in enumerate(self._split_long_text(section_text)):
                cleaned = part.strip()
                if not cleaned:
                    continue
                chunk_index = len(chunks)
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"{path.name}#chunk_{chunk_index:04d}",
                        file_name=path.name,
                        section_title=section_title or doc_title,
                        text=cleaned,
                        topic=topic,
                        subtopics=subtopics,
                        aliases=aliases,
                        char_count=len(cleaned),
                    )
                )
        return chunks

    def _attach_neighbors(self, chunks: list[KnowledgeChunk]) -> None:
        by_file: dict[str, list[KnowledgeChunk]] = {}
        for chunk in chunks:
            by_file.setdefault(chunk.file_name, []).append(chunk)
        for file_chunks in by_file.values():
            for idx, chunk in enumerate(file_chunks):
                if idx > 0:
                    chunk.prev_chunk_id = file_chunks[idx - 1].chunk_id
                if idx < len(file_chunks) - 1:
                    chunk.next_chunk_id = file_chunks[idx + 1].chunk_id

    def _attach_embeddings(self, chunks: list[KnowledgeChunk]) -> None:
        if not chunks:
            return
        self._last_embedding_error = False
        try:
            for start in range(0, len(chunks), 16):
                batch = chunks[start : start + 16]
                texts = [self._embedding_text(chunk) for chunk in batch]
                embeddings = self.embedding_client.embed_texts(texts)
                for chunk, embedding in zip(batch, embeddings):
                    chunk.embedding = embedding
        except RuntimeError:
            self._last_embedding_error = True
            for chunk in chunks:
                chunk.embedding = None

    def _embedding_text(self, chunk: KnowledgeChunk) -> str:
        metadata = " ".join([chunk.topic, *chunk.subtopics, *chunk.aliases])
        return f"{chunk.section_title}\n{metadata}\n{chunk.text}"

    def _write_index(self, chunks: list[KnowledgeChunk]) -> None:
        lines = [
            json.dumps(asdict(chunk), ensure_ascii=False, separators=(",", ":"))
            for chunk in chunks
        ]
        self.chunks_path.write_text("\n".join(lines), encoding="utf-8")
        manifest = {
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "chunk_count": len(chunks),
            "chunk_size": self.chunk_size,
            "embedding_model": self.embedding_client.model,
            "embedding_enabled": any(chunk.embedding for chunk in chunks),
            "embedding_api_key_available": bool(self.embedding_client.api_key),
            "embedding_error": self._last_embedding_error,
            "source_files": self._source_fingerprint(),
        }
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_index(self) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        for line in self.chunks_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            chunks.append(KnowledgeChunk.from_dict(json.loads(stripped)))
        return chunks

    def _prefilter_files(
        self,
        chunks: list[KnowledgeChunk],
        query_text: str,
        query_terms: set[str],
        config: RetrievalConfig,
    ) -> set[str]:
        scores: dict[str, float] = {}
        for chunk in chunks:
            metadata_text = self._normalize(
                " ".join([chunk.file_name, chunk.topic, chunk.section_title, *chunk.subtopics, *chunk.aliases])
            )
            score = 0.0
            if chunk.topic and self._normalize(chunk.topic) in query_text:
                score += 4.0
            score += sum(2.0 for alias in chunk.aliases if alias and self._normalize(alias) in query_text)
            score += sum(1.0 for term in query_terms if term and term in metadata_text)
            scores[chunk.file_name] = max(scores.get(chunk.file_name, 0.0), score)

        positive = [(name, score) for name, score in scores.items() if score > 0]
        if not positive:
            return {chunk.file_name for chunk in chunks}
        positive.sort(key=lambda item: item[1], reverse=True)
        return {name for name, _ in positive[: config.candidate_files_limit]}

    def _embed_query(self, query: str) -> list[float] | None:
        try:
            return self.embedding_client.embed_text(query)
        except RuntimeError:
            return None

    def _hybrid_recall(
        self,
        *,
        candidates: list[KnowledgeChunk],
        query_text: str,
        query_terms: set[str],
        query_embedding: list[float] | None,
        config: RetrievalConfig,
    ) -> list[RetrievedChunk]:
        sparse_rows = [
            RetrievedChunk(
                chunk=chunk,
                sparse_score=self._score_sparse(chunk, query_text, query_terms),
                metadata_score=self._score_metadata(chunk, query_text, query_terms),
            )
            for chunk in candidates
        ]
        sparse_rows = [row for row in sparse_rows if row.sparse_score > 0 or row.metadata_score > 0]
        sparse_rows.sort(key=lambda row: row.sparse_score + row.metadata_score, reverse=True)
        sparse_rows = sparse_rows[: config.top_k_sparse]

        dense_rows: list[RetrievedChunk] = []
        if query_embedding is not None:
            for chunk in candidates:
                if chunk.embedding:
                    dense_score = self._cosine_similarity(query_embedding, chunk.embedding)
                    if dense_score > 0:
                        dense_rows.append(RetrievedChunk(chunk=chunk, dense_score=dense_score))
            dense_rows.sort(key=lambda row: row.dense_score, reverse=True)
            dense_rows = dense_rows[: config.top_k_dense]

        merged: dict[str, RetrievedChunk] = {}
        for row in [*sparse_rows, *dense_rows]:
            existing = merged.get(row.chunk.chunk_id)
            if existing is None:
                merged[row.chunk.chunk_id] = row
                continue
            existing.sparse_score = max(existing.sparse_score, row.sparse_score)
            existing.dense_score = max(existing.dense_score, row.dense_score)
            existing.metadata_score = max(existing.metadata_score, row.metadata_score)

        rows = list(merged.values())
        if not rows:
            return []
        self._normalize_scores(rows, "sparse_score")
        self._normalize_scores(rows, "dense_score")
        self._normalize_scores(rows, "metadata_score")
        for row in rows:
            row.recall_score = (
                0.45 * row.sparse_score
                + 0.45 * row.dense_score
                + 0.10 * row.metadata_score
            )
            row.final_score = row.recall_score
        rows.sort(key=lambda row: row.final_score, reverse=True)
        return rows[: config.merge_top_n]

    def _score_sparse(self, chunk: KnowledgeChunk, query_text: str, query_terms: set[str]) -> float:
        title_text = self._normalize(chunk.section_title)
        chunk_text = self._normalize(chunk.text)
        title_hits = sum(1 for term in query_terms if term in title_text)
        early_hits = sum(1 for term in query_terms if term in chunk_text[:260])
        text_hits = sum(1 for term in query_terms if term in chunk_text)
        phrase_hit = 2.0 if query_text and query_text in chunk_text else 0.0
        return title_hits * 4.0 + early_hits * 1.5 + text_hits * 0.6 + phrase_hit

    def _score_metadata(self, chunk: KnowledgeChunk, query_text: str, query_terms: set[str]) -> float:
        metadata_text = self._normalize(" ".join([chunk.topic, *chunk.subtopics, *chunk.aliases]))
        alias_hits = sum(1 for alias in chunk.aliases if alias and self._normalize(alias) in query_text)
        term_hits = sum(1 for term in query_terms if term in metadata_text)
        return alias_hits * 3.0 + term_hits

    def _rule_rerank(
        self,
        rows: list[RetrievedChunk],
        query_text: str,
        query_terms: set[str],
    ) -> list[RetrievedChunk]:
        for row in rows:
            chunk = row.chunk
            title_text = self._normalize(chunk.section_title)
            chunk_text = self._normalize(chunk.text)
            metadata_text = self._normalize(" ".join([chunk.topic, *chunk.subtopics, *chunk.aliases]))
            title_match = sum(1 for term in query_terms if term in title_text)
            alias_match = sum(1 for term in query_terms if term in metadata_text)
            keyword_density = sum(1 for term in query_terms if term in chunk_text[:300])
            same_topic_boost = 1.0 if chunk.topic and self._normalize(chunk.topic) in query_text else 0.0
            question_type_boost = self._question_type_boost(query_text, title_text, chunk_text)
            row.rerank_score = (
                0.35 * title_match
                + 0.25 * alias_match
                + 0.20 * keyword_density
                + 0.10 * same_topic_boost
                + 0.10 * question_type_boost
            )
            row.final_score = 0.60 * row.recall_score + 0.40 * row.rerank_score
        rows.sort(key=lambda row: row.final_score, reverse=True)
        return rows

    def _llm_rerank(
        self,
        query: str,
        rows: list[RetrievedChunk],
        config: RetrievalConfig,
    ) -> list[RetrievedChunk]:
        if not config.use_llm_rerank or self.llm_client is None or not rows:
            return rows[: config.final_top_k]

        candidates = rows[: config.llm_rerank_top_n]
        prompt = self._build_llm_rerank_prompt(query, candidates, config.final_top_k)
        try:
            payload = self.llm_client.chat_json(
                system_prompt=(
                    "你是课程知识库检索结果的排序器。"
                    "只根据候选片段是否能回答问题排序，不要补充外部知识。"
                    "只输出 JSON。"
                ),
                user_prompt=prompt,
                temperature=0.0,
            )
        except RuntimeError:
            return rows[: config.final_top_k]

        ranked_ids = payload.get("ranked_chunk_ids", [])
        if not isinstance(ranked_ids, list):
            return rows[: config.final_top_k]

        by_id = {row.chunk.chunk_id: row for row in candidates}
        reranked: list[RetrievedChunk] = []
        for chunk_id in ranked_ids:
            row = by_id.get(str(chunk_id))
            if row is not None and row not in reranked:
                row.final_score += max(0.0, 1.0 - len(reranked) * 0.08)
                reranked.append(row)
            if len(reranked) >= config.final_top_k:
                break

        if len(reranked) < config.final_top_k:
            for row in rows:
                if row not in reranked:
                    reranked.append(row)
                if len(reranked) >= config.final_top_k:
                    break
        return reranked[: config.final_top_k]

    def _build_llm_rerank_prompt(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        final_top_k: int,
    ) -> str:
        blocks: list[str] = [f"问题：{query}", "候选片段："]
        for idx, row in enumerate(candidates, start=1):
            chunk = row.chunk
            text = self._truncate_text(chunk.text, 240)
            blocks.append(
                f"[{idx}]\n"
                f"chunk_id: {chunk.chunk_id}\n"
                f"标题: {chunk.section_title}\n"
                f"内容: {text}"
            )
        blocks.append(
            "请选出最能回答问题的片段并按相关性排序。"
            f"最多返回 {final_top_k} 个 chunk_id。"
            '返回格式：{"ranked_chunk_ids": ["..."], "reason": "简短说明"}'
        )
        return "\n\n".join(blocks)

    def _expand_and_pack(
        self,
        rows: list[RetrievedChunk],
        config: RetrievalConfig,
    ) -> list[KnowledgeChunk]:
        selected: list[KnowledgeChunk] = []
        seen: set[str] = set()
        for row in rows:
            chunk = row.chunk
            if chunk.chunk_id in seen:
                continue
            selected.append(chunk)
            seen.add(chunk.chunk_id)
            if len(selected) >= config.final_top_k:
                break

        packed: list[KnowledgeChunk] = []
        used_chars = 0
        max_chars_per_chunk = 320 if config.mode == "qa" else 260
        for chunk in selected:
            text = self._truncate_text(chunk.text, max_chars_per_chunk)
            next_chunk = self._chunk_by_id.get(chunk.next_chunk_id or "")
            if (
                next_chunk is not None
                and next_chunk.file_name == chunk.file_name
                and next_chunk.section_title == chunk.section_title
                and used_chars + len(text) + min(len(next_chunk.text), 180) <= config.token_budget
            ):
                text = f"{text}\n{self._truncate_text(next_chunk.text, 180)}"

            remaining = config.token_budget - used_chars
            if remaining <= 80:
                break
            if len(text) > remaining:
                text = self._truncate_text(text, remaining)
            packed.append(
                KnowledgeChunk(
                    chunk_id=chunk.chunk_id,
                    file_name=chunk.file_name,
                    section_title=chunk.section_title,
                    text=text,
                    topic=chunk.topic,
                    subtopics=chunk.subtopics,
                    aliases=chunk.aliases,
                    char_count=len(text),
                    prev_chunk_id=chunk.prev_chunk_id,
                    next_chunk_id=chunk.next_chunk_id,
                    embedding=None,
                )
            )
            used_chars += len(text)
        return packed

    def _format_chunk(self, index: int, chunk: KnowledgeChunk) -> str:
        return (
            f"[{index}] 文件: {chunk.file_name}\n"
            f"SOURCE: {chunk.file_name}\n"
            f"标题: {chunk.section_title}\n"
            f"TITLE: {chunk.section_title}\n"
            f"内容:\n{chunk.text}"
        )

    def _parse_front_matter(self, content: str) -> tuple[dict[str, str | list[str]], str]:
        normalized = content.replace("\r\n", "\n")
        if not normalized.startswith("---\n"):
            return {}, normalized

        end_marker = normalized.find("\n---\n", 4)
        if end_marker == -1:
            return {}, normalized

        raw_metadata = normalized[4:end_marker]
        body = normalized[end_marker + 5 :]
        metadata: dict[str, str | list[str]] = {}
        for line in raw_metadata.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue
            key, raw_value = stripped.split(":", 1)
            metadata[key.strip()] = self._parse_front_matter_value(raw_value.strip())
        return metadata, body

    def _parse_front_matter_value(self, raw_value: str) -> str | list[str]:
        value = raw_value.strip().strip('"').strip("'")
        if value.startswith("[") and value.endswith("]"):
            return [
                item.strip().strip('"').strip("'")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
        return value

    def _split_content_by_headings(
        self,
        content: str,
        default_title: str,
    ) -> list[tuple[str, str]]:
        chunks: list[tuple[str, str]] = []
        heading_stack: list[tuple[int, str]] = [(1, default_title)]
        buffer: list[str] = []
        in_code_block = False

        for line in content.replace("\r\n", "\n").split("\n"):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                buffer.append(line)
                continue

            heading_match = None if in_code_block else re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                if level == 1:
                    heading_stack = [(1, title)]
                    continue
                if buffer and any(part.strip() for part in buffer):
                    chunks.append((self._compose_title(heading_stack), "\n".join(buffer).strip()))
                    buffer = []
                heading_stack = [item for item in heading_stack if item[0] < level]
                heading_stack.append((level, title))
                continue

            buffer.append(line)

        if buffer and any(part.strip() for part in buffer):
            chunks.append((self._compose_title(heading_stack), "\n".join(buffer).strip()))
        return chunks

    def _compose_title(self, heading_stack: list[tuple[int, str]]) -> str:
        return " > ".join(title for _, title in heading_stack if title.strip())

    def _split_long_text(self, text: str) -> list[str]:
        cleaned = text.strip()
        if len(cleaned) <= self.chunk_size:
            return [cleaned]

        paragraphs = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
        if not paragraphs:
            return [cleaned]

        chunks: list[str] = []
        current: list[str] = []
        current_len = 0
        for paragraph in paragraphs:
            if len(paragraph) > self.chunk_size:
                if current:
                    chunks.append("\n\n".join(current))
                    current = []
                    current_len = 0
                for start in range(0, len(paragraph), self.chunk_size):
                    chunks.append(paragraph[start : start + self.chunk_size].strip())
                continue

            next_len = current_len + len(paragraph) + (2 if current else 0)
            if current and next_len > self.chunk_size:
                chunks.append("\n\n".join(current))
                current = [paragraph]
                current_len = len(paragraph)
                continue
            current.append(paragraph)
            current_len = next_len

        if current:
            chunks.append("\n\n".join(current))
        return chunks or [cleaned]

    def _question_type_boost(self, query_text: str, title_text: str, chunk_text: str) -> float:
        if any(keyword in query_text for keyword in ("区别", "比较", "对比", "difference", "compare")):
            if any(keyword in title_text for keyword in ("区别", "比较", "对比")):
                return 12.0
            if any(keyword in title_text for keyword in ("例题", "实现", "代码")):
                return -8.0
            return 0.0
        if any(keyword in query_text for keyword in ("定义", "概念", "是什么", "what is")):
            return 3.0 if any(keyword in title_text for keyword in ("定义", "概念", "基本")) else 0.0
        if any(keyword in query_text for keyword in ("实现", "代码", "操作", "怎么", "如何", "how")):
            return 2.0 if any(keyword in title_text for keyword in ("实现", "操作", "算法", "结构定义")) else 0.0
        if any(keyword in query_text for keyword in ("复杂度", "时间复杂度", "空间复杂度", "complexity")):
            if any(keyword in title_text for keyword in ("复杂度", "性能")):
                return 3.0
            return 1.0 if "复杂度" in chunk_text[:160] else 0.0
        if any(keyword in query_text for keyword in ("例题", "题", "练习", "易错")):
            return 2.0 if any(keyword in title_text for keyword in ("例题", "错误", "难点")) else 0.0
        return 0.0

    def _tokenize(self, text: str) -> set[str]:
        normalized = self._normalize(text)
        if not normalized:
            return set()

        parts = [
            part.strip()
            for part in re.split(r"[\s,.;:!?(){}\[\]<>/\\|+=*&^%$#@~`\"'，。；：！？（）【】《》“”‘’、]+", normalized)
            if part.strip()
        ]
        terms: set[str] = set()
        for part in parts:
            if part in self.STOP_TERMS:
                continue
            if re.fullmatch(r"[a-z0-9_+#-]+", part):
                if len(part) >= 2:
                    terms.add(part)
                continue
            if len(part) >= 2 or self._contains_cjk(part):
                terms.add(part)
            min_length = 1 if self._contains_cjk(part) else 2
            for length in range(min(6, len(part)), min_length - 1, -1):
                for start in range(0, len(part) - length + 1):
                    sub = part[start : start + length]
                    if sub not in self.STOP_TERMS:
                        terms.add(sub)
        return {term for term in terms if term.strip()}

    def _normalize(self, text: str) -> str:
        lowered = text.lower().replace("\r\n", "\n")
        table = str.maketrans(
            {
                "，": " ",
                "。": " ",
                "；": " ",
                "：": " ",
                "！": " ",
                "？": " ",
                "（": " ",
                "）": " ",
                "【": " ",
                "】": " ",
                "《": " ",
                "》": " ",
                "\t": " ",
                "\n": " ",
            }
        )
        return re.sub(r"\s+", " ", lowered.translate(table)).strip()

    def _ensure_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()] if str(value).strip() else []

    def _infer_topic(self, path: Path) -> str:
        stem = path.stem.lower()
        if "tree" in stem:
            return "tree_and_binarytree"
        return stem

    def _contains_cjk(self, text: str) -> bool:
        return any("\u4e00" <= char <= "\u9fff" for char in text)

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return max(0.0, dot / (left_norm * right_norm))

    def _normalize_scores(self, rows: list[RetrievedChunk], attr: str) -> None:
        max_score = max(getattr(row, attr) for row in rows)
        if max_score <= 0:
            return
        for row in rows:
            setattr(row, attr, getattr(row, attr) / max_score)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        cleaned = re.sub(r"\n{3,}", "\n\n", text.strip())
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[: max(0, max_chars - 1)].rstrip() + "…"
