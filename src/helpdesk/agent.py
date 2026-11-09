"""The agent loop: guard input -> retrieve KB context -> LLM with tools -> run tools -> final answer."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from .guardrails import is_injection, redact
from .tools import TOOL_SCHEMAS, HelpdeskTools

SYSTEM_PROMPT = """You are the IT Service Desk assistant for employees.
Answer ONLY from the knowledge-base context below. Cite the source file in square brackets, e.g. [vpn.md].
If the context says to raise a ticket, or the steps do not solve the problem, call create_ticket.
If the user asks whether a service is down or slow, call check_service_status.
If the context does not contain the answer, say you don't know and offer to raise a ticket.
Never ask for or repeat passwords, MFA codes or other secrets.

Context:
{context}"""

REFUSAL = ("I can't help with that request. I can answer IT questions from the knowledge base "
           "or raise a ticket for you.")


@dataclass
class AgentResult:
    answer: str
    sources: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    blocked: bool = False
    latency_ms: float = 0.0


class HelpdeskAgent:
    def __init__(self, llm, retriever, tools: HelpdeskTools, k: int = 3, max_steps: int = 3):
        self.llm, self.retriever, self.tools = llm, retriever, tools
        self.k, self.max_steps = k, max_steps

    def answer(self, question: str) -> AgentResult:
        t0 = time.perf_counter()
        if is_injection(question):
            return AgentResult(REFUSAL, blocked=True, latency_ms=(time.perf_counter() - t0) * 1000)

        question = redact(question)                       # secrets never reach the model or logs
        hits = self.retriever.search(question, self.k)
        context = "\n\n".join(f"[{c.source}] {c.text}" for c, _ in hits)
        messages = [{"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
                    {"role": "user", "content": question}]
        calls: list[dict] = []

        reply = {"content": ""}
        for _ in range(self.max_steps):
            reply = self.llm.chat(messages, tools=TOOL_SCHEMAS)
            tool_calls = reply.get("tool_calls") or []
            if not tool_calls:
                break
            messages.append(reply)
            for tc in tool_calls:
                fn = tc.get("function", {})
                args = fn.get("arguments") or {}
                if isinstance(args, str):                 # some models return JSON as a string
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                result = self.tools.call(fn.get("name", ""), args)
                calls.append({"name": fn.get("name"), "arguments": args, "result": result})
                messages.append({"role": "tool", "content": json.dumps(result)})

        return AgentResult(
            answer=redact(reply.get("content", "").strip()),
            sources=list(dict.fromkeys(c.source for c, _ in hits)),
            tool_calls=calls,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )
