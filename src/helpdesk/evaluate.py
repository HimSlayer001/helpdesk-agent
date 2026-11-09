"""Benchmark retrieval and the full agent on the labelled question set.

    python -m helpdesk.evaluate                # everything (needs Ollama running)
    python -m helpdesk.evaluate --retrieval-only --retrievers bm25   # offline, no Ollama

Writes results/results.json and results/results.md.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from .agent import HelpdeskAgent
from .kb import load_kb
from .retriever import BM25Retriever, DenseRetriever, HybridRetriever
from .tools import HelpdeskTools


def load_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def pct(vals, p):
    s = sorted(vals)
    return s[min(len(s) - 1, max(0, round(p / 100 * len(s)) - 1))] if s else 0.0


def eval_retrieval(retriever, questions, k=3):
    qs = [q for q in questions if q["expected_source"]]
    hit1 = hitk = rr = 0.0
    for q in qs:
        srcs = [c.source for c, _ in retriever.search(q["question"], k)]
        if srcs and srcs[0] == q["expected_source"]:
            hit1 += 1
        if q["expected_source"] in srcs:
            hitk += 1
            rr += 1 / (srcs.index(q["expected_source"]) + 1)
    n = len(qs)
    return {"queries": n, "hit@1": hit1 / n, f"hit@{k}": hitk / n, f"mrr@{k}": rr / n}


def eval_agent(agent: HelpdeskAgent, questions, injections):
    tool_ok = cite_ok = cite_n = 0
    lat, false_blocks, rows = [], 0, []
    for q in questions:
        r = agent.answer(q["question"])
        lat.append(r.latency_ms)
        false_blocks += r.blocked
        called = {c["name"] for c in r.tool_calls}
        ok = (q["expected_tool"] in called) if q["expected_tool"] else not called
        tool_ok += ok
        if q["expected_source"]:
            cite_n += 1
            cite_ok += f"[{q['expected_source']}]" in r.answer
        rows.append({"question": q["question"], "tool_ok": ok, "called": sorted(called),
                     "answer": r.answer[:300], "latency_ms": round(r.latency_ms)})
    blocked = sum(agent.answer(q["question"]).blocked for q in injections)
    return {
        "questions": len(questions),
        "tool_selection_accuracy": tool_ok / len(questions),
        "citation_accuracy": cite_ok / max(cite_n, 1),
        "injection_block_rate": blocked / max(len(injections), 1),
        "false_block_rate": false_blocks / len(questions),
        "latency_p50_ms": statistics.median(lat),
        "latency_p95_ms": pct(lat, 95),
        "per_question": rows,
    }


def to_markdown(res):
    out = []
    if res.get("retrieval"):
        out += ["| Retriever | Hit@1 | Hit@3 | MRR@3 |", "|---|---|---|---|"]
        for name, m in res["retrieval"].items():
            out.append(f"| {name} | {m['hit@1']:.2f} | {m['hit@3']:.2f} | {m['mrr@3']:.2f} |")
    if res.get("agent"):
        a = res["agent"]
        out += ["", "| Agent metric | Value |", "|---|---|",
                f"| Tool-selection accuracy | {a['tool_selection_accuracy']:.0%} |",
                f"| Citation accuracy | {a['citation_accuracy']:.0%} |",
                f"| Prompt-injection block rate | {a['injection_block_rate']:.0%} |",
                f"| False block rate | {a['false_block_rate']:.0%} |",
                f"| Latency p50 / p95 | {a['latency_p50_ms']:.0f} / {a['latency_p95_ms']:.0f} ms |"]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default="kb")
    ap.add_argument("--retrievers", default="bm25,dense,hybrid")
    ap.add_argument("--retrieval-only", action="store_true")
    ap.add_argument("--agent-retriever", default="hybrid")
    args = ap.parse_args()

    questions = load_jsonl("eval/questions.jsonl")
    injections = load_jsonl("eval/injections.jsonl")
    chunks = load_kb(args.kb)
    bm25 = BM25Retriever(chunks)
    retrievers = {"bm25": bm25}
    names = args.retrievers.split(",")
    if "dense" in names or "hybrid" in names or not args.retrieval_only:
        from .llm import EMBED_MODEL, ollama_embed
        dense = DenseRetriever(chunks, ollama_embed)
        retrievers.update({"dense": dense, "hybrid": HybridRetriever(bm25, dense)})

    res = {"run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
           "machine": f"{platform.system()} {platform.machine()}",
           "kb_chunks": len(chunks), "retrieval": {}, "agent": None}
    for name in names:
        res["retrieval"][name] = eval_retrieval(retrievers[name], questions)
        print(name, res["retrieval"][name])

    if not args.retrieval_only:
        from .llm import CHAT_MODEL, EMBED_MODEL, OllamaLLM
        res.update(chat_model=CHAT_MODEL, embed_model=EMBED_MODEL, agent_retriever=args.agent_retriever)
        agent = HelpdeskAgent(OllamaLLM(), retrievers[args.agent_retriever], HelpdeskTools(":memory:", f"{args.kb}/service_status.json"))
        t0 = time.time()
        res["agent"] = eval_agent(agent, questions, injections)
        print({k: v for k, v in res["agent"].items() if k != "per_question"}, f"{time.time()-t0:.0f}s")

    Path("results").mkdir(exist_ok=True)
    Path("results/results.json").write_text(json.dumps(res, indent=2))
    Path("results/results.md").write_text(to_markdown(res) + "\n")
    print("\n" + to_markdown(res))


if __name__ == "__main__":
    main()
