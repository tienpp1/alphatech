"""
Vector and Hybrid retrieval service with strict workspace isolation, cosine similarity ranking,
lexical keyword boosting, and confidence threshold filtering.
"""

import os
import re
import unicodedata
from typing import Any, Dict, List, Optional
import numpy as np
from django.conf import settings
from apps.workspaces.models import Workspace
from apps.knowledge.models import DocumentChunk, DocumentStatus
from apps.knowledge.embedding import get_embedding


def calculate_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _normalize_vietnamese_text(text: str) -> str:
    """Normalizes text by removing diacritics and converting to lowercase."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accent = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accent.replace("đ", "d").replace("Đ", "d").lower().strip()


def calculate_lexical_score(query: str, content: str, title: str = "", heading: str = "") -> float:
    """Computes normalized lexical keyword overlap score."""
    q_norm = _normalize_vietnamese_text(query)
    stopwords = {"la", "va", "cua", "cac", "nhung", "cho", "trong", "tai", "ve", "duoc", "theo", "khi", "neu", "mot", "nhieu", "co", "thi"}
    tokens = [w for w in re.findall(r"\b\w{2,}\b", q_norm) if w not in stopwords]
    if not tokens:
        tokens = re.findall(r"\b\w+\b", q_norm)
    if not tokens:
        return 0.0

    target = _normalize_vietnamese_text(f"{title} {heading} {content}")
    unique_tokens = set(tokens)
    matched = sum(1 for t in unique_tokens if t in target)
    return float(matched / len(unique_tokens))


def search_relevant_chunks(
    workspace: Workspace,
    query: str,
    top_k: Optional[int] = None,
    threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Performs hybrid semantic vector + lexical keyword search across document chunks
    belonging strictly to the active workspace.
    Filters by similarity >= threshold, ranks descending, and limits to top_k.
    """
    if not query or not query.strip():
        return []

    top_k = top_k if top_k is not None else getattr(settings, "RAG_TOP_K", 5)
    if threshold is None:
        api_key = getattr(settings, "LLM_API_KEY", "")
        if api_key and str(api_key).strip():
            threshold = float(getattr(settings, "RAG_SIMILARITY_THRESHOLD", 0.70))
        else:
            # Calibrated baseline for deterministic projection in offline/CI environments
            threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.10"))

    # 1. Compute query vector
    query_vec = get_embedding(query)
    q_norm = np.linalg.norm(query_vec)
    if q_norm == 0.0:
        return []

    # 2. Fetch candidate chunks scoped strictly to the workspace
    chunk_qs = (
        DocumentChunk.objects.for_workspace(workspace)
        .filter(document__status=DocumentStatus.READY)
        .select_related("document")
    )

    scored_chunks: List[Dict[str, Any]] = []

    for chunk in chunk_qs:
        chunk_vec = chunk.embedding
        if not chunk_vec:
            continue

        dense_sim = calculate_cosine_similarity(query_vec, chunk_vec)
        # Check dense vector against threshold to eliminate out-of-domain queries
        if dense_sim >= threshold:
            heading = chunk.metadata.get("heading") or ""
            doc_title = chunk.document.title
            lex_score = calculate_lexical_score(query, chunk.content, doc_title, heading)

            # Hybrid blend: dense semantic score + lexical match boost
            blended_sim = round(float(0.75 * dense_sim + 0.25 * (dense_sim * (1.0 + lex_score))), 4)
            final_sim = max(round(float(dense_sim), 4), blended_sim)

            scored_chunks.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document.id,
                "document_title": doc_title,
                "content": chunk.content,
                "page_number": chunk.metadata.get("page_number"),
                "heading": heading,
                "source_file": chunk.metadata.get("source_file") or doc_title,
                "similarity": final_sim,
                "dense_similarity": round(float(dense_sim), 4),
                "lexical_score": round(float(lex_score), 4),
            })

    # 3. Sort descending by similarity score
    scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)

    return scored_chunks[:top_k]
