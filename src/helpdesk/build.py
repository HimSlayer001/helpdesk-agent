"""Wire up the default agent: KB -> hybrid retriever (BM25 + Ollama embeddings) -> Ollama chat model."""
from __future__ import annotations

import os

from .agent import HelpdeskAgent
from .kb import load_kb
from .llm import OllamaLLM, ollama_embed
from .retriever import BM25Retriever, DenseRetriever, HybridRetriever
from .tools import HelpdeskTools


def build_agent(kb_dir: str = "kb", db_path: str | None = None, retriever: str = "hybrid") -> HelpdeskAgent:
    chunks = load_kb(kb_dir)
    bm25 = BM25Retriever(chunks)
    if retriever == "bm25":
        r = bm25
    else:
        dense = DenseRetriever(chunks, ollama_embed)
        r = dense if retriever == "dense" else HybridRetriever(bm25, dense)
    tools = HelpdeskTools(db_path or os.environ.get("TICKETS_DB", "tickets.db"), f"{kb_dir}/service_status.json")
    return HelpdeskAgent(OllamaLLM(), r, tools)
