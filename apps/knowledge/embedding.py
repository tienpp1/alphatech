import hashlib
import json
import math
import re
import urllib.request
import urllib.error
from typing import List, Optional
from django.conf import settings


VI_STOPWORDS = {
    "và", "của", "là", "trong", "các", "được", "có", "tại", "ngày", "không",
    "cho", "với", "những", "về", "đến", "từ", "này", "đó", "hay", "thì",
    "mà", "như", "gì", "sao", "bao", "nhiêu", "ai", "đâu", "khi", "lúc",
    "nào", "một", "hai", "ba", "bốn", "năm", "ở", "ra", "vào", "lên", "xuống",
}


def _generate_deterministic_embedding(text: str, dimension: int) -> List[float]:
    """
    Generates a deterministic L2-normalized pseudo-semantic embedding vector
    based on term frequency and n-gram hash projection with stop word suppression.
    Provides reliable, reproducible similarity scores for testing and offline environments.
    """
    vector = [0.0] * dimension
    clean_text = text.lower().strip()
    all_words = re.findall(r"\w+", clean_text, re.UNICODE)
    words = [w for w in all_words if w not in VI_STOPWORDS]

    if not words:
        words = all_words

    if not words:
        # Uniform vector for empty string
        val = 1.0 / math.sqrt(dimension)
        return [val] * dimension

    # 1. Unigram projection
    for w in words:
        # Generate stable bucket index and sign
        h = int(hashlib.sha256(w.encode("utf-8")).hexdigest(), 16)
        idx = h % dimension
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vector[idx] += sign * 1.0

    # 2. Bigram projection (preserves local phrase semantics)
    for i in range(len(words) - 1):
        bigram = f"{words[i]}_{words[i+1]}"
        h = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16)
        idx = h % dimension
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vector[idx] += sign * 1.5

    # 3. L2 Normalization
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        return [round(x / norm, 6) for x in vector]

    val = 1.0 / math.sqrt(dimension)
    return [val] * dimension


def _call_gemini_embedding_api(text: str, model_name: str, api_key: str) -> Optional[List[float]]:
    """Invokes Google Gemini embedContent REST API using urllib."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:embedContent?key={api_key}"
    payload = {
        "model": f"models/{model_name}",
        "content": {"parts": [{"text": text[:8000]}]},
    }
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                values = data.get("embedding", {}).get("values")
                if values and isinstance(values, list):
                    norm = math.sqrt(sum(x * x for x in values))
                    if norm > 0:
                        return [x / norm for x in values]
                    return values
    except Exception:
        pass
    return None


def _call_openai_embedding_api(text: str, model_name: str, api_key: str) -> Optional[List[float]]:
    """Invokes OpenAI embeddings REST API using urllib."""
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": text[:8000],
        "model": model_name,
    }
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                results = data.get("data", [])
                if results and "embedding" in results[0]:
                    return results[0]["embedding"]
    except Exception:
        pass
    return None


def get_embedding(text: str, dimension: Optional[int] = None) -> List[float]:
    """
    Computes an L2-normalized vector embedding for the input text.
    Uses configured external LLM API if key is present, otherwise falls back
    to deterministic vector projection.
    """
    dim = dimension or getattr(settings, "EMBEDDING_DIMENSION", 768)
    model = getattr(settings, "EMBEDDING_MODEL", "text-embedding-004")
    provider = getattr(settings, "LLM_PROVIDER", "gemini").lower()
    api_key = getattr(settings, "LLM_API_KEY", "")

    if api_key and api_key.strip():
        if provider == "gemini":
            result = _call_gemini_embedding_api(text, model, api_key)
            if result:
                return result
        elif provider == "openai":
            result = _call_openai_embedding_api(text, model, api_key)
            if result:
                return result

    # Offline / Test / Fallback
    return _generate_deterministic_embedding(text, dim)


def get_embeddings_batch(texts: List[str], dimension: Optional[int] = None) -> List[List[float]]:
    """Batch computes embeddings for a list of strings."""
    return [get_embedding(t, dimension=dimension) for t in texts]
