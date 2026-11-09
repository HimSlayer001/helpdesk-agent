"""HTTP API:  uvicorn helpdesk.api:app --app-dir src --port 8000"""
from fastapi import FastAPI
from pydantic import BaseModel

from .build import build_agent

app = FastAPI(title="IT Helpdesk Agent")
_agent = None


def agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


class Ask(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(body: Ask):
    r = agent().answer(body.question)
    return {"answer": r.answer, "sources": r.sources, "tool_calls": r.tool_calls,
            "blocked": r.blocked, "latency_ms": round(r.latency_ms, 1)}
