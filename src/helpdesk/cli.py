"""Chat with the helpdesk agent in the terminal:  python -m helpdesk.cli"""
from .build import build_agent


def main():
    agent = build_agent()
    print("IT Helpdesk agent. Ask an IT question (Ctrl+C to quit).\n")
    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        r = agent.answer(q)
        print(f"\nagent> {r.answer}")
        for c in r.tool_calls:
            print(f"   [tool] {c['name']}({c['arguments']}) -> {c['result']}")
        if r.sources:
            print(f"   [sources] {', '.join(r.sources)}   [{r.latency_ms:.0f} ms]")
        print()


if __name__ == "__main__":
    main()
