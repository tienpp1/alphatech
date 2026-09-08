"""
Recursive Text Chunking Engine with configurable window and overlap.
Preserves segment metadata (page numbers, section headings, document references).
"""

from typing import Any, Dict, List, Optional
from django.conf import settings


class RecursiveTextChunker:
    """
    Splits text recursively using natural boundary separators (\n\n, \n, sentence, word)
    while maintaining a sliding overlap window.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.chunk_size = chunk_size or getattr(settings, "RAG_CHUNK_SIZE", 500)
        self.chunk_overlap = chunk_overlap or getattr(settings, "RAG_CHUNK_OVERLAP", 100)

        if self.chunk_overlap >= self.chunk_size:
            self.chunk_overlap = max(0, self.chunk_size // 4)

    def _split_text_recursively(self, text: str, separators: List[str]) -> List[str]:
        """Recursively breaks text down until parts are <= chunk_size."""
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            # Hard split on character boundary as last resort
            chunks = []
            start = 0
            while start < len(text):
                chunks.append(text[start : start + self.chunk_size])
                start += self.chunk_size - self.chunk_overlap
            return chunks

        sep = separators[0]
        remaining_seps = separators[1:]

        if sep:
            splits = text.split(sep)
        else:
            splits = list(text)

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for piece in splits:
            piece_len = len(piece) + (len(sep) if current_chunk else 0)

            if current_len + piece_len <= self.chunk_size:
                current_chunk.append(piece)
                current_len += piece_len
            else:
                if current_chunk:
                    chunk_text = sep.join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(chunk_text)
                    # Slide overlap window
                    overlap_len = 0
                    overlap_pieces: List[str] = []
                    for p in reversed(current_chunk):
                        if overlap_len + len(p) <= self.chunk_overlap:
                            overlap_pieces.insert(0, p)
                            overlap_len += len(p)
                        else:
                            break
                    current_chunk = overlap_pieces
                    current_len = sum(len(p) for p in current_chunk) + (len(sep) * max(0, len(current_chunk) - 1))

                if len(piece) > self.chunk_size:
                    sub_chunks = self._split_text_recursively(piece, remaining_seps)
                    chunks.extend(sub_chunks)
                else:
                    current_chunk.append(piece)
                    current_len += len(piece) + (len(sep) if len(current_chunk) > 1 else 0)

        if current_chunk:
            final_text = sep.join(current_chunk).strip()
            if final_text and (not chunks or chunks[-1] != final_text):
                chunks.append(final_text)

        return chunks

    def chunk_segments(
        self,
        segments: List[Dict[str, Any]],
        source_title: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Takes raw parsed segments from parsers.py and outputs standardized
        chunk dictionaries with continuous chunk_index and metadata.
        """
        separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]
        all_chunks: List[Dict[str, Any]] = []
        chunk_idx = 1

        for seg in segments:
            text = seg.get("text", "").strip()
            if not text:
                continue

            page_num = seg.get("page_number")
            heading = seg.get("heading")

            raw_pieces = self._split_text_recursively(text, separators)

            for piece in raw_pieces:
                clean_piece = piece.strip()
                if not clean_piece:
                    continue

                approx_tokens = max(1, len(clean_piece.split()))
                all_chunks.append({
                    "chunk_index": chunk_idx,
                    "content": clean_piece,
                    "token_count": approx_tokens,
                    "metadata": {
                        "page_number": page_num,
                        "heading": heading,
                        "source_file": source_title,
                    },
                })
                chunk_idx += 1

        return all_chunks
