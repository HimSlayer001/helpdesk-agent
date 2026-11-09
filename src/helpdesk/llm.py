"""Minimal Ollama client (chat with tool calling, embeddings) using only the standard library."""
from __future__ import annotations

import json
import os
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "llama3.2:3b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")


def _post(path: str, payload: dict, timeout: float = 120) -> dict:
    req = urllib.request.Request(f"{OLLAMA_URL}{path}", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


class OllamaLLM:
    def __init__(self, model: str = CHAT_MODEL, temperature: float = 0.0):
        self.model, self.temperature = model, temperature

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """Returns the assistant message: {"role", "content", optional "tool_calls"}."""
        payload = {"model": self.model, "messages": messages, "stream": False,
                   "options": {"temperature": self.temperature}}
        if tools:
            payload["tools"] = tools
        return _post("/api/chat", payload)["message"]


def ollama_embed(texts: list[str], model: str = EMBED_MODEL) -> list[list[float]]:
    return _post("/api/embed", {"model": model, "input": texts})["embeddings"]
