# 🚀 Next Step: Steps 5 + 6 — Markdown Renderer & Orchestrator

**Why these two together?** They're both medium-to-low effort, and completing them gives you the **first working end-to-end pipeline** — real data in, real `OWUI_INDEX.md` out. You get a usable artifact *today*, then enrich it with community data later.

---

## 📊 Progress Map

| # | Step | Status | Priority |
|---|------|--------|----------|
| 1 | API Discovery & Swagger | ✅ Done | — |
| 2 | `local_api.py` collector | ✅ Done | — |
| 4 | Pydantic schemas | ✅ Done | — |
| **5** | **Jinja2 Markdown template** | **👈 NOW** | 🟡 Medium / Low Effort |
| **6** | **`generate_index.py` orchestrator** | **👈 NOW** | 🟡 Medium / Medium Effort |
| 3 | `community_scraper.py` | 🔜 Next after | 🔴 High / Medium Effort |
| 7–11 | Integration, Advisor, Cron, Actions | ⏳ Later | 🟢 Nice-to-have |

---

## 📝 Step 5: Jinja2 Markdown Template (`templates/index.md.j2`)

This is the **presentation layer** — it takes the validated Pydantic `OWUIIndex` object and renders it into the `OWUI_INDEX.md` structure we designed in the plan.

### What to Build

```
owui_index_generator/
├── templates/
│   └── index.md.j2          # ← THIS FILE
├── renderers/
│   └── markdown.py           # ← AND THIS FILE
```

### `templates/index.md.j2` — Must Include These Sections

| Section | Data Source | Key Columns |
|---------|-----------|-------------|
| **Header** | `OWUIIndex.generated_at`, `.instance_url`, `.version` | Timestamp, URL, version |
| **Summary Table** | Counts from each list in `OWUIIndex` | Category / Installed / Available |
| **🔧 Tools — Installed** | `OWUIIndex.tools` | Name, ID, Description, Author, Status |
| **⚙️ Functions — Installed** | `OWUIIndex.functions` | Name, ID, **Type** (Pipe/Filter/Action), Description, Global?, Assigned Models |
| **🤖 Models** | `OWUIIndex.models` | Name, ID, Provider, Base Model, Tools Attached, Knowledge Attached |
| **📝 Prompts** | `OWUIIndex.prompts` | Name, Command (`/slash`), Description |
| **📚 Knowledge** | `OWUIIndex.knowledge` | Name, Description, File Count |
| **🏷️ Tag Index** | Cross-reference all entries by tags/categories | Tag → List of extension names |
| **🔲 Community (Placeholder)** | Empty for now — will be populated by Step 3 | "Run community scraper to populate" |

### `renderers/markdown.py` — Key Logic

```python
# Pseudocode structure
from jinja2 import Environment, FileSystemLoader
from schema.extension import OWUIIndex

def render_index(index: OWUIIndex) -> str:
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("index.md.j2")
    return template.render(index=index)

def save_index(content: str, path: str = "/app/backend/data/OWUI_INDEX.md"):
    with open(path, "w") as f:
        f.write(content)
```

### Template Design Tips

| Tip | Why |
|-----|-----|
| Use Jinja2 `{% for %}` loops with `{% if %}` guards for empty lists | Graceful handling when tools=[] |
| Use `{{ entry.description \| truncate(120) }}` | Keep table rows readable |
| Group functions by `entry.type` using `{% if entry.type == 'pipe' %}` etc. | Clean separation of Pipes vs Filters vs Actions |
| Add `<!-- COMMUNITY_TOOLS_START -->` markers | Makes it easy for Step 3 scraper to inject data later |
| Escape pipe characters in descriptions: `{{ desc \| replace('\|', '∣') }}` | Prevent broken Markdown tables |

---

## ⚙️ Step 6: `generate_index.py` — The Orchestrator

This is the **main entry point** that wires everything together.

### What It Does (Sequentially)

```
┌─────────────────────────────────────────────────────┐
│                 generate_index.py                     │
│                                                       │
│  1. Load config (.env / config.yaml)                 │
│  2. Call local_api.py → get OWUIIndex object         │
│  3. (Future) Call community_scraper.py → merge       │
│  4. (Future) Call github_repos.py → merge            │
│  5. Call renderers/markdown.py → render to string    │
│  6. Save OWUI_INDEX.md to data directory             │
│  7. Save owui_index.json (raw structured backup)     │
│  8. Print summary stats to console                   │
│  9. Exit with status code                            │
└─────────────────────────────────────────────────────┘
```

### Skeleton Structure

```python
#!/usr/bin/env python3
"""Open WebUI Extension Index Generator"""

import argparse
import logging
from datetime import datetime, timezone

from collectors.local_api import collect_local_data
# from collectors.community_scraper import collect_community_data  # Step 3
# from collectors.github_repos import collect_github_data          # Future
from renderers.markdown import render_index, save_index

def main():
    parser = argparse.ArgumentParser(description="Generate OWUI_INDEX.md")
    parser.add_argument("--output-dir", default="/app/backend/data/")
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--md-only", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    # 1. Collect local data
    index = collect_local_data()

    # 2. (Future) Enrich with community data
    # community = collect_community_data()
    # index = merge(index, community)

    # 3. Render & Save
    if not args.json_only:
        md_content = render_index(index)
        save_index(md_content, path=f"{args.output_dir}/OWUI_INDEX.md")

    if not args.md_only:
        save_json(index, path=f"{args.output_dir}/owui_index.json")

    # 4. Summary
    print_summary(index)

if __name__ == "__main__":
    main()
```

### CLI Usage When Done

```bash
# Full generation (both .md and .json)
python generate_index.py --output-dir ./data/

# Just the markdown
python generate_index.py --md-only

# Verbose logging for debugging
python generate_index.py -v
```

---

## ✅ Definition of Done for Steps 5+6

- [ ] `python generate_index.py` runs end-to-end without errors
- [ ] `OWUI_INDEX.md` is generated with all local data populated
- [ ] `owui_index.json` is saved alongside as structured backup
- [ ] Empty sections (tools=[], community=placeholder) render gracefully — not broken tables
- [ ] Console prints a summary like:

```
✅ OWUI_INDEX.md generated successfully
   📍 /app/backend/data/OWUI_INDEX.md
   🤖 Models:     14
   🔧 Tools:       0 (install some from openwebui.com/tools!)
   ⚙️ Functions:   0
   📝 Prompts:     2
   📚 Knowledge:   3
   ⏱️  Generated:  2026-02-23T12:00:00Z
```

---

## 🎯 Why This Sequence Matters

```
Steps 1+2+4 (DONE)     Steps 5+6 (NOW)         Step 3 (NEXT)
━━━━━━━━━━━━━━━━━━━    ━━━━━━━━━━━━━━━━━━━     ━━━━━━━━━━━━━━━━━━
API data collected  →   Rendered into usable  →  Enriched with 
& validated              OWUI_INDEX.md            community catalog
                               │
                               ▼
                    🎉 FIRST WORKING MVP
                    (Agent can already use this!)
```

After Steps 5+6, you'll have a **real, working index** of your instance. Then Step 3 (community scraper) will transform it from "what I have" into "what I have **+ what I could have**" — which is where the agent recommendation magic happens.