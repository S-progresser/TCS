from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

rulebooks = json.loads((DATA_DIR / "rulebooks.json").read_text(encoding="utf-8"))
sources = json.loads((DATA_DIR / "sources.json").read_text(encoding="utf-8"))
chunks = []
for rule in rulebooks:
    chunks.append({
        "id": f"chunk-{rule['id']}",
        "title": rule['title'],
        "text": f"{rule['summary']} Source: {rule['source']}",
        "source": rule['source'],
        "tags": rule['keywords'],
    })
for source in sources:
    chunks.append({
        "id": f"source-{source['title'].lower().replace(' ', '-')}",
        "title": source['title'],
        "text": source['summary'],
        "source": source['source'],
        "tags": ["guidance", "insurance", "claim"],
    })
(DATA_DIR / "kb_chunks.json").write_text(json.dumps(chunks, indent=2), encoding="utf-8")
print(f"Ingested {len(chunks)} knowledge chunks to {DATA_DIR / 'kb_chunks.json'}")
