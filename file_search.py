import math
from typing import List, Dict
from PyPDF2 import PdfReader

from .client import client
from .logger import create_logger
from .constants import GPT4_MODEL

logger = create_logger(__name__)

# in-memory vector store: user_id -> list of {"embedding": [float], "text": str}
vector_store: Dict[int, List[Dict]] = {}


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _cosine(a: List[float], b: List[float]) -> float:
    return _dot(a, b) / math.sqrt(_dot(a, a) * _dot(b, b))


async def _embed(text: str) -> List[float]:
    resp = await client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding


def _chunk(text: str, size: int = 1000) -> List[str]:
    return [text[i:i + size] for i in range(0, len(text), size)]


async def process_pdf(user_id: int, file_path: str) -> str:
    logger.info(f"process_pdf:start:{user_id}:{file_path}")
    reader = PdfReader(file_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    chunks = _chunk(text)

    embeddings = []
    for chunk in chunks:
        emb = await _embed(chunk)
        embeddings.append({"embedding": emb, "text": chunk})
    vector_store[user_id] = embeddings
    logger.info(f"process_pdf:stored:{user_id}:{len(embeddings)}_chunks")

    summary_prompt = f"Summarize the following text:\n{text}"[:8000]
    response = await client.chat.completions.create(
        model=GPT4_MODEL,
        messages=[{"role": "user", "content": summary_prompt}]
    )
    summary = response.choices[0].message.content.strip()
    logger.info(f"process_pdf:summary_done:{user_id}")
    return summary


async def search_context(user_id: int, query: str) -> str:
    docs = vector_store.get(user_id)
    if not docs:
        logger.info(f"search_context:no_docs:{user_id}")
        return ""
    query_emb = await _embed(query)
    best = max(docs, key=lambda d: _cosine(query_emb, d["embedding"]))
    logger.info(f"search_context:found:{user_id}")
    return best["text"]


def clear_store(user_id: int):
    vector_store.pop(user_id, None)
