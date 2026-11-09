"""Copy the measured results into README.md between the RESULTS markers."""
import json
import re
from pathlib import Path

from .evaluate import to_markdown

START, END = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"


def main():
    res = json.loads(Path("results/results.json").read_text())
    head = (f"Measured {res['run_at_utc']} UTC on {res['machine']}; {res['kb_chunks']} KB chunks, "
            f"25 labelled questions + 4 injection attempts.")
    if res.get("agent"):
        head += f" Chat model `{res['chat_model']}`, embeddings `{res['embed_model']}`, agent uses {res['agent_retriever']} retrieval."
    block = f"{START}\n{head}\n\n{to_markdown(res)}\n{END}"
    p = Path("README.md")
    p.write_text(re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: block, p.read_text(), flags=re.S))
    print("README.md updated")


if __name__ == "__main__":
    main()
