"""Load the Markdown knowledge base and split it into section-level chunks."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    id: str        # e.g. "vpn.md#common-errors"
    source: str    # file name, used for citations
    title: str     # "VPN access (GlobalConnect) > Common errors"
    text: str


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def chunk_markdown(source: str, text: str) -> list[Chunk]:
    """One chunk per '## ' section, each prefixed with the page title so it stands alone."""
    lines = text.strip().splitlines()
    page_title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("# ") else source
    chunks, heading, buf = [], "Overview", []

    def flush():
        body = "\n".join(buf).strip()
        if body:
            title = f"{page_title} > {heading}"
            chunks.append(Chunk(f"{source}#{_slug(heading)}", source, title, f"{title}\n{body}"))

    for line in lines[1:]:
        if line.startswith("## "):
            flush()
            heading, buf = line[3:].strip(), []
        else:
            buf.append(line)
    flush()
    return chunks


def load_kb(folder: str | Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(Path(folder).glob("*.md")):
        chunks.extend(chunk_markdown(path.name, path.read_text(encoding="utf-8")))
    return chunks
