

# Stage 2: Agent Integration & Autonomous Maintenance

## Objective

Turn the static `OWUI_INDEX.md` / `owui_index.json` into a **live, queryable knowledge layer** that any model on the instance can tap into — and that maintains itself without manual intervention.

**End state:** A user types *"I need something that can generate images"* and the system searches the index, recommends matching tools/functions, and walks them through installation — all from within a chat.

---

## Prerequisites Checklist

Before starting, confirm each of these is true:

| # | Requirement | How to Verify |
|---|-------------|---------------|
| 1 | `generate_index.py --community` runs clean | `python generate_index.py --community --pages 1` exits 0 |
| 2 | `data/owui_index.json` exists and is valid JSON | `python -c "import json; json.load(open('data/owui_index.json'))"` |
| 3 | `data/OWUI_INDEX.md` exists and is non-empty | `wc -l data/OWUI_INDEX.md` returns > 50 |
| 4 | API key is set and working | `curl -H "Authorization: Bearer $WEBUI_API_KEY" http://localhost:7860/api/models` returns JSON |
| 5 | At least one capable model is available | GPT-4o, Claude 3.5, or Qwen3 32B+ accessible via OpenRouter or local |
| 6 | `.venv` is activated with all deps installed | `pip list \| grep jinja2` returns a hit |

---

## Execution Order & Dependency Graph

```
Step 7A: Knowledge Ingestion Script
  │
  ├──→ Step 7B: Extension Search Tool (uses owui_index.json directly)
  │       │
  │       └──→ Step 7C: Extension Advisor Model Preset
  │               (attaches Knowledge from 7A + Tool from 7B)
  │
  └──→ Step 7D: Regeneration Action Function
          │
          └──→ Step 7E: Scheduled Refresh (cron wrapping 7D's logic)

  [Bonus] GitHub Repos Collector ──→ feeds into generate_index.py
```

**Estimated total effort:** 4–6 focused hours across 1–2 sessions.

---

## Step 7A: Knowledge Base Ingestion

**Goal:** Programmatically upload `OWUI_INDEX.md` into Open WebUI's Knowledge system so any model can RAG-retrieve from it.

**Deliverables:**
```
owui_index_generator/
└── uploaders/
    └── knowledge_sync.py      # Uploads/updates the index in Knowledge
```

### Implementation

```python
"""
knowledge_sync.py
Uploads or replaces the OWUI_INDEX.md file in an Open WebUI Knowledge collection.

Workflow:
  1. Upload the .md file via POST /api/v1/files/
  2. Create or update a Knowledge collection via the Knowledge API
  3. Attach the uploaded file to that collection
"""

import os
import sys
import json
import requests
from pathlib import Path

class KnowledgeSync:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
        }
        self.collection_name = "OWUI Extension Index"
        self.collection_description = (
            "Auto-generated catalog of all installed and available "
            "Open WebUI extensions — tools, functions, models, prompts, "
            "pipelines, and MCP servers."
        )

    def upload_file(self, filepath: str) -> dict:
        """Upload a file and return the file metadata."""
        url = f"{self.base_url}/api/v1/files/"
        filename = Path(filepath).name

        with open(filepath, "rb") as f:
            resp = requests.post(
                url,
                headers=self.headers,
                files={"file": (filename, f, "text/markdown")},
            )
        resp.raise_for_status()
        file_data = resp.json()
        print(f"  ✅ File uploaded: {file_data.get('id')} ({filename})")
        return file_data

    def find_existing_collection(self) -> dict | None:
        """Check if our Knowledge collection already exists."""
        url = f"{self.base_url}/api/v1/knowledge/"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        collections = resp.json()

        for col in collections:
            if col.get("name") == self.collection_name:
                return col
        return None

    def create_collection(self, file_id: str) -> dict:
        """Create a new Knowledge collection with the file attached."""
        url = f"{self.base_url}/api/v1/knowledge/create"
        payload = {
            "name": self.collection_name,
            "description": self.collection_description,
            "data": {"file_ids": [file_id]},
        }
        resp = requests.post(url, headers=self.headers, json=payload)
        resp.raise_for_status()
        col = resp.json()
        print(f"  ✅ Collection created: {col.get('id')}")
        return col

    def update_collection(self, collection_id: str, file_id: str) -> dict:
        """
        Replace the file in an existing collection.
        Steps:
          1. Remove old files from the collection
          2. Add the new file
        """
        # Add new file to collection
        url = f"{self.base_url}/api/v1/knowledge/{collection_id}/file/add"
        resp = requests.post(
            url,
            headers=self.headers,
            json={"file_id": file_id},
        )
        resp.raise_for_status()
        print(f"  ✅ Collection updated: {collection_id}")
        return resp.json()

    def remove_old_files(self, collection_id: str, keep_file_id: str):
        """Remove all files from collection except the one we just uploaded."""
        url = f"{self.base_url}/api/v1/knowledge/{collection_id}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        col = resp.json()

        existing_files = col.get("data", {}).get("file_ids", [])
        for fid in existing_files:
            if fid != keep_file_id:
                remove_url = (
                    f"{self.base_url}/api/v1/knowledge/{collection_id}"
                    f"/file/remove"
                )
                requests.post(
                    remove_url,
                    headers=self.headers,
                    json={"file_id": fid},
                )
                print(f"  🗑️  Removed old file: {fid}")

    def sync(self, filepath: str):
        """Main entry point: upload file and sync to Knowledge."""
        print(f"📤 Syncing {filepath} to Knowledge...")

        # 1. Upload the file
        file_data = self.upload_file(filepath)
        file_id = file_data["id"]

        # 2. Find or create the collection
        existing = self.find_existing_collection()

        if existing:
            col_id = existing["id"]
            print(f"  📂 Found existing collection: {col_id}")
            self.update_collection(col_id, file_id)
            self.remove_old_files(col_id, file_id)
        else:
            print("  📂 No existing collection found, creating new...")
            self.create_collection(file_id)

        print("✅ Knowledge sync complete.")
        return file_id


def main():
    base_url = os.getenv("OWUI_BASE_URL", "http://localhost:7860")
    api_key = os.getenv("WEBUI_API_KEY", "")

    if not api_key:
        print("❌ WEBUI_API_KEY not set.")
        sys.exit(1)

    index_path = Path(__file__).parent.parent.parent / "data" / "OWUI_INDEX.md"
    if not index_path.exists():
        print(f"❌ Index file not found at {index_path}")
        print("   Run generate_index.py first.")
        sys.exit(1)

    syncer = KnowledgeSync(base_url, api_key)
    syncer.sync(str(index_path))


if __name__ == "__main__":
    main()
```

### Verification
```bash
# Run it
cd /path/to/project
python -m owui_index_generator.uploaders.knowledge_sync

# Confirm via API
curl -s -H "Authorization: Bearer $WEBUI_API_KEY" \
  http://localhost:7860/api/v1/knowledge/ | python -m json.tool

# Expected: collection named "OWUI Extension Index" with 1 file attached
```

### Potential API Gotchas to Watch For
The Knowledge API endpoints may vary slightly between Open WebUI versions. If any endpoint 404s:
1. Check Swagger at `http://localhost:7860/docs` (requires `ENV=dev`)
2. Look for `/api/v1/knowledge` vs `/api/knowledge` variations
3. File upload may need `multipart/form-data` vs JSON — the code above handles this

**Effort:** ~45 minutes (including API exploration and debugging)

---

## Step 7B: Extension Search Tool

**Goal:** A proper Open WebUI **Tool** that any model can invoke to search the index programmatically — returning structured, actionable results.

**Deliverable:**
```
owui_index_generator/
└── tools/
    └── extension_search.py    # The Tool to paste into Open WebUI
```

### Implementation

```python
"""
title: Extension Catalog Search
author: Cortextia
author_url: https://github.com/Averocore/cortextia
version: 1.0.0
description: Searches the OWUI extension index to find tools, functions, models, and prompts matching a user's needs. Returns structured recommendations with install links.
required_open_webui_version: 0.4.0
"""

import json
import os
from typing import Optional
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        index_path: str = Field(
            default="/app/backend/data/owui_index.json",
            description="Path to the owui_index.json file inside the container",
        )
        max_results: int = Field(
            default=10,
            description="Maximum number of results to return per search",
        )

    def __init__(self):
        self.valves = self.Valves()
        self._index_cache = None
        self._cache_mtime = 0

    def _load_index(self) -> dict:
        """Load index with simple file-mtime caching."""
        path = self.valves.index_path
        if not os.path.exists(path):
            return {}

        mtime = os.path.getmtime(path)
        if self._index_cache is None or mtime > self._cache_mtime:
            with open(path, "r") as f:
                self._index_cache = json.load(f)
            self._cache_mtime = mtime

        return self._index_cache

    def _score_match(self, query_terms: list[str], text: str) -> int:
        """Simple relevance scoring: count how many query terms appear."""
        text_lower = text.lower()
        return sum(1 for term in query_terms if term in text_lower)

    def search_extensions(
        self,
        query: str,
        category: Optional[str] = None,
    ) -> str:
        """
        Search for Open WebUI extensions (tools, functions, models, prompts)
        that match a described need or keyword.

        Use this when a user asks about capabilities, wants recommendations,
        or asks "is there a tool/function for X?"

        :param query: What the user needs, e.g. "web search", "image generation",
                      "code execution", "TTS", "RAG", etc.
        :param category: Optional filter — one of: "tools", "functions", "models",
                         "prompts", "community_tools", "community_functions".
                         Leave empty to search everything.
        :return: Formatted list of matching extensions with install info.
        """
        index = self._load_index()
        if not index:
            return (
                "⚠️ Extension index not found. "
                "Please run the index generator first: "
                "`python generate_index.py --community`"
            )

        query_terms = [t.strip().lower() for t in query.split() if len(t) > 2]
        if not query_terms:
            return "Please provide a more specific search query."

        results = []

        # --- Search installed tools ---
        if category in (None, "tools"):
            for tool in index.get("tools", []):
                searchable = f"{tool.get('name', '')} {tool.get('description', '')}"
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    results.append({
                        "score": score,
                        "type": "🔧 Installed Tool",
                        "name": tool.get("name", "Unknown"),
                        "id": tool.get("id", ""),
                        "description": tool.get("description", "")[:120],
                        "status": "✅ Installed",
                        "action": "Already available — assign to a model in Workspace > Models",
                    })

        # --- Search installed functions ---
        if category in (None, "functions"):
            for func in index.get("functions", []):
                searchable = (
                    f"{func.get('name', '')} {func.get('description', '')} "
                    f"{func.get('function_type', '')}"
                )
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    ftype = func.get("function_type", "unknown").title()
                    results.append({
                        "score": score,
                        "type": f"⚙️ Installed Function ({ftype})",
                        "name": func.get("name", "Unknown"),
                        "id": func.get("id", ""),
                        "description": func.get("description", "")[:120],
                        "status": "✅ Installed",
                        "action": "Already available — check Workspace > Functions",
                    })

        # --- Search community tools ---
        if category in (None, "community_tools"):
            for ext in index.get("community_extensions", []):
                if ext.get("type") != "tool":
                    continue
                searchable = f"{ext.get('name', '')} {ext.get('description', '')}"
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    results.append({
                        "score": score,
                        "type": "🌐 Community Tool",
                        "name": ext.get("name", "Unknown"),
                        "id": ext.get("slug", ""),
                        "description": ext.get("description", "")[:120],
                        "status": "📥 Available",
                        "action": f"Install → {ext.get('url', 'openwebui.com')}",
                        "downloads": ext.get("downloads", 0),
                        "author": ext.get("author", ""),
                    })

        # --- Search community functions ---
        if category in (None, "community_functions"):
            for ext in index.get("community_extensions", []):
                if ext.get("type") != "function":
                    continue
                searchable = f"{ext.get('name', '')} {ext.get('description', '')}"
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    results.append({
                        "score": score,
                        "type": "🌐 Community Function",
                        "name": ext.get("name", "Unknown"),
                        "id": ext.get("slug", ""),
                        "description": ext.get("description", "")[:120],
                        "status": "📥 Available",
                        "action": f"Install → {ext.get('url', 'openwebui.com')}",
                        "downloads": ext.get("downloads", 0),
                        "author": ext.get("author", ""),
                    })

        # --- Search models ---
        if category in (None, "models"):
            for model in index.get("models", []):
                searchable = f"{model.get('name', '')} {model.get('id', '')}"
                score = self._score_match(query_terms, searchable)
                if score > 0:
                    results.append({
                        "score": score,
                        "type": "🤖 Model",
                        "name": model.get("name", "Unknown"),
                        "id": model.get("id", ""),
                        "description": f"Provider: {model.get('provider', 'unknown')}",
                        "status": "✅ Available",
                        "action": "Select in chat model dropdown",
                    })

        if not results:
            return (
                f"No extensions found matching '{query}'.\n\n"
                f"💡 Suggestions:\n"
                f"- Try broader terms (e.g., 'search' instead of 'SearXNG')\n"
                f"- Browse the community: https://openwebui.com/tools\n"
                f"- Check if the index is up to date"
            )

        # Sort by relevance score, then by downloads for community items
        results.sort(
            key=lambda r: (r["score"], r.get("downloads", 0)),
            reverse=True,
        )
        results = results[: self.valves.max_results]

        # Format output
        lines = [f"## 🔍 Search Results for: \"{query}\"\n"]
        lines.append(f"Found **{len(results)}** matching extensions:\n")

        for i, r in enumerate(results, 1):
            lines.append(f"### {i}. {r['name']}")
            lines.append(f"- **Type:** {r['type']}")
            lines.append(f"- **ID:** `{r['id']}`")
            lines.append(f"- **Description:** {r['description']}")
            lines.append(f"- **Status:** {r['status']}")
            if r.get("author"):
                lines.append(f"- **Author:** @{r['author']}")
            if r.get("downloads"):
                lines.append(f"- **Downloads:** {r['downloads']:,}")
            lines.append(f"- **Action:** {r['action']}")
            lines.append("")

        lines.append("---")
        lines.append(
            "⚠️ **Security:** Only install extensions from trusted sources. "
            "Review code before importing."
        )

        return "\n".join(lines)

    def get_index_summary(self) -> str:
        """
        Get a high-level summary of the extension index — how many tools,
        functions, models, and community extensions are cataloged.

        Use this when a user asks "what do we have?" or "show me the overview."

        :return: Summary statistics of the extension index.
        """
        index = self._load_index()
        if not index:
            return "⚠️ Extension index not found."

        tools = len(index.get("tools", []))
        functions = len(index.get("functions", []))
        models = len(index.get("models", []))
        prompts = len(index.get("prompts", []))
        knowledge = len(index.get("knowledge", []))
        community = len(index.get("community_extensions", []))

        comm_tools = sum(
            1 for e in index.get("community_extensions", [])
            if e.get("type") == "tool"
        )
        comm_funcs = sum(
            1 for e in index.get("community_extensions", [])
            if e.get("type") == "function"
        )

        generated = index.get("generated_at", "unknown")

        return (
            f"## 📊 Extension Index Summary\n\n"
            f"**Last generated:** {generated}\n\n"
            f"| Category | Count |\n"
            f"|----------|-------|\n"
            f"| Installed Tools | {tools} |\n"
            f"| Installed Functions | {functions} |\n"
            f"| Available Models | {models} |\n"
            f"| Prompts | {prompts} |\n"
            f"| Knowledge Bases | {knowledge} |\n"
            f"| Community Tools (catalog) | {comm_tools} |\n"
            f"| Community Functions (catalog) | {comm_funcs} |\n"
            f"| **Total Cataloged** | **{tools + functions + models + prompts + community}** |\n"
        )
```

### Installation Procedure
1. In Open WebUI, navigate to **Workspace → Tools → ➕ Create**
2. Paste the entire contents of `extension_search.py`
3. Click **Save**
4. Go to **Workspace → Models** → select your preferred model → enable the tool
5. Configure the **Valve** `index_path` if your data directory differs

### Verification
Start a chat with the model that has the tool attached and test:

```
User: "I need something for web search"
Expected: Tool is invoked, returns matching community tools with install links

User: "What extensions do we have?"
Expected: get_index_summary is invoked, returns the stats table

User: "Find me image generation tools"
Expected: Matching results from community catalog
```

**Effort:** ~30 minutes (mostly testing tool invocation behavior)

---

## Step 7C: Extension Advisor Model Preset

**Goal:** A dedicated model persona that combines the Knowledge base (RAG) + the Search Tool + a crafted system prompt into a single selectable "advisor" in the chat dropdown.

**Deliverable:** A model preset created via the Open WebUI UI (documented here for reproducibility).

### Configuration

**Navigate to:** Workspace → Models → ➕ Create a Model

| Field | Value |
|-------|-------|
| **Name** | `Extension Advisor` |
| **Model ID** | `extension-advisor` |
| **Base Model** | Your best available reasoning model (GPT-4o / Claude 3.5 / Qwen3 32B+) |
| **Description** | Recommends, explains, and helps install Open WebUI extensions |
| **Avatar** | 🧩 or upload a custom icon |

### System Prompt

```markdown
You are the **Extension Advisor** for this Open WebUI instance. Your role is to
help users discover, evaluate, and install the right extensions for their needs.

## How You Work

1. **When a user describes a need**, use the `search_extensions` tool to find
   matching tools, functions, or models. Present the top results with clear
   recommendations.

2. **When a user asks "what do we have?"**, use the `get_index_summary` tool
   for an overview, then offer to drill into any category.

3. **When recommending**, always explain:
   - What the extension does (one sentence)
   - Whether it's a **Tool** (LLM-invoked at runtime) vs **Function**
     (modifies WebUI behavior) vs **Pipeline** (separate server process)
   - Installation steps specific to the extension type
   - Any prerequisites: API keys, external services, model requirements
   - Whether it needs **native function calling** (GPT-4o, Claude, Qwen3 32B+)
     or works in **default/prompt mode** (any model)

4. **When helping install**, provide step-by-step:
   - For community extensions: "Go to Workspace → Tools/Functions → click the
     ➕ button → Import from URL → paste: [URL]"
   - For GitHub-sourced: "Copy the raw .py file content → Workspace →
     Tools/Functions → Create → paste code → Save"
   - Mention any **Valves** (settings) that need configuration post-install

5. **Security**: Always remind users that extensions execute arbitrary Python
   on the server. Only install from trusted sources. Review code before importing.

## What You Know

You have access to a continuously updated Extension Index containing:
- All installed tools, functions, models, prompts, and knowledge bases
- A catalog of community tools and functions from openwebui.com
- Download counts, authors, and descriptions for community extensions

## Personality

Be concise, practical, and opinionated. If two tools do the same thing,
recommend the better one and explain why. If nothing matches, say so and suggest
how one could be built or where to look next.

Do NOT hallucinate extensions that don't exist in the index. If unsure, search
first, then respond.
```

### Attachments

| Attachment Type | What to Attach |
|-----------------|----------------|
| **Knowledge** | `OWUI Extension Index` (the collection created in Step 7A) |
| **Tools** | `Extension Catalog Search` (the tool created in Step 7B) |

### Verification

Open a new chat, select **Extension Advisor** from the model dropdown, and run these test conversations:

```
Test 1 — Discovery:
  User: "I want to add web search to my chats"
  Expected: Searches index → recommends SearXNG tool or similar →
            provides install link → notes API key requirements

Test 2 — Overview:
  User: "Give me a summary of what's available"
  Expected: Calls get_index_summary → shows stats table →
            offers to explore categories

Test 3 — Comparison:
  User: "What's the difference between a Tool and a Function?"
  Expected: Clear explanation from system prompt knowledge,
            no tool invocation needed

Test 4 — Install guidance:
  User: "How do I install the Memory function?"
  Expected: Searches for it → provides step-by-step install →
            mentions any Valves to configure

Test 5 — Edge case:
  User: "Is there a tool for controlling my smart home?"
  Expected: Searches → finds N8N or Home Assistant if indexed →
            or honestly says "nothing found, here's how you could build one"
```

**Effort:** ~20 minutes (UI configuration + testing)

---

## Step 7D: Index Regeneration Action Function

**Goal:** A button in the chat UI that triggers a full index regeneration without leaving the browser or touching a terminal.

**Deliverable:**
```
owui_index_generator/
└── tools/
    └── index_regenerator.py   # Action Function for Open WebUI
```

### Design Decision: Tool vs Action vs Filter

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Tool** | LLM can invoke it conversationally | Runs during inference, may timeout on large scrapes | ❌ |
| **Action** | Dedicated UI button, clear user intent | Requires specific function signature | ✅ Best fit |
| **Filter** | Could auto-trigger on certain messages | Overly complex, wrong abstraction | ❌ |

We'll build it as a **Tool** with a manual invocation pattern, since Action functions have a specific UI integration pattern that may change between versions. The Tool approach is more portable.

### Implementation

```python
"""
title: Index Regenerator
author: Cortextia
author_url: https://github.com/Averocore/cortextia
version: 1.0.0
description: Regenerates the OWUI Extension Index by re-querying local APIs and the community catalog. Run this after installing or removing extensions.
required_open_webui_version: 0.4.0
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        owui_base_url: str = Field(
            default="http://localhost:7860",
            description="Base URL of the Open WebUI instance (internal)",
        )
        api_key: str = Field(
            default="",
            description="Open WebUI API key (Bearer token)",
        )
        output_dir: str = Field(
            default="/app/backend/data",
            description="Directory where index files are written",
        )
        community_pages: int = Field(
            default=1,
            description="Number of pages to fetch from the community catalog (per type)",
        )
        include_community: bool = Field(
            default=True,
            description="Whether to include community catalog in regeneration",
        )

    def __init__(self):
        self.valves = self.Valves()

    def regenerate_index(self) -> str:
        """
        Regenerate the Open WebUI Extension Index.

        This re-queries all local API endpoints and optionally the community
        catalog, then writes updated owui_index.json and OWUI_INDEX.md files.

        Use this after installing, removing, or updating extensions,
        or when the user asks to "refresh" or "update" the index.

        :return: Status message with regeneration results.
        """
        import requests

        base = self.valves.owui_base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {self.valves.api_key}"}
        out_dir = self.valves.output_dir

        if not self.valves.api_key:
            return (
                "❌ API key not configured. Set the `api_key` Valve in "
                "Workspace → Tools → Index Regenerator → Valves."
            )

        report = []
        report.append("## 🔄 Index Regeneration Report\n")
        report.append(f"**Started:** {datetime.now(timezone.utc).isoformat()}\n")

        index_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "instance_url": base,
        }

        # --- Local API Collection ---
        endpoints = {
            "models": "/api/models",
            "tools": "/api/v1/tools",
            "functions": "/api/v1/functions",
            "prompts": "/api/prompts",
            "knowledge": "/api/v1/knowledge",
        }

        for key, path in endpoints.items():
            try:
                resp = requests.get(f"{base}{path}", headers=headers, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                # Normalize: some endpoints return {"data": [...]}
                if isinstance(data, dict) and "data" in data:
                    items = data["data"]
                elif isinstance(data, list):
                    items = data
                else:
                    items = []

                index_data[key] = items
                report.append(f"- ✅ `{key}`: {len(items)} items")
            except Exception as e:
                index_data[key] = []
                report.append(f"- ❌ `{key}`: Failed — {str(e)[:80]}")

        # --- Community Catalog (optional) ---
        if self.valves.include_community:
            report.append("\n**Community catalog:**")
            community = []

            for ext_type in ["tools", "functions"]:
                for page in range(1, self.valves.community_pages + 1):
                    try:
                        api_url = (
                            f"https://openwebui.com/api/v1/community/"
                            f"{ext_type}/search?page={page}&limit=100"
                        )
                        resp = requests.get(api_url, timeout=20)
                        resp.raise_for_status()
                        items = resp.json()

                        if isinstance(items, dict):
                            items = items.get("data", items.get("items", []))

                        for item in items:
                            community.append({
                                "type": ext_type.rstrip("s"),
                                "name": item.get("name", ""),
                                "slug": item.get("slug", ""),
                                "description": item.get("description", "")[:200],
                                "author": item.get("author", {}).get(
                                    "username", ""
                                ) if isinstance(item.get("author"), dict)
                                else str(item.get("author", "")),
                                "downloads": item.get("downloads", 0),
                                "url": f"https://openwebui.com/"
                                       f"{'t' if ext_type == 'tools' else 'f'}/"
                                       f"{item.get('author', {}).get('username', '_')}/"
                                       f"{item.get('slug', '')}",
                            })
                        report.append(
                            f"- ✅ Community {ext_type} page {page}: "
                            f"{len(items)} items"
                        )
                    except Exception as e:
                        report.append(
                            f"- ❌ Community {ext_type} page {page}: "
                            f"{str(e)[:80]}"
                        )

            index_data["community_extensions"] = community
            report.append(f"- **Total community items:** {len(community)}")

        # --- Write JSON ---
        json_path = os.path.join(out_dir, "owui_index.json")
        try:
            with open(json_path, "w") as f:
                json.dump(index_data, f, indent=2, default=str)
            report.append(f"\n📄 JSON written to `{json_path}`")
        except Exception as e:
            report.append(f"\n❌ JSON write failed: {e}")

        # --- Write Markdown (simplified inline version) ---
        md_path = os.path.join(out_dir, "OWUI_INDEX.md")
        try:
            md_lines = [
                f"# 🗂️ Open WebUI Extension Index",
                f"> Auto-generated: {index_data['generated_at']}",
                f"> Instance: {base}\n",
                f"## 📊 Summary",
                f"| Category | Count |",
                f"|----------|-------|",
                f"| Models | {len(index_data.get('models', []))} |",
                f"| Tools | {len(index_data.get('tools', []))} |",
                f"| Functions | {len(index_data.get('functions', []))} |",
                f"| Prompts | {len(index_data.get('prompts', []))} |",
                f"| Knowledge | {len(index_data.get('knowledge', []))} |",
                f"| Community Catalog | "
                f"{len(index_data.get('community_extensions', []))} |",
                "",
            ]
            with open(md_path, "w") as f:
                f.write("\n".join(md_lines))
            report.append(f"📄 Markdown written to `{md_path}`")
        except Exception as e:
            report.append(f"❌ Markdown write failed: {e}")

        report.append(
            f"\n**Completed:** {datetime.now(timezone.utc).isoformat()}"
        )
        return "\n".join(report)
```

### Installation & Configuration
1. Paste into **Workspace → Tools → Create**
2. Save, then open **Valves** (⚙️ icon):
   - Set `api_key` to your Open WebUI API key
   - Verify `owui_base_url` matches your instance
   - Adjust `community_pages` (1 = ~100 items per type, 3 = ~300)
3. Attach the tool to the **Extension Advisor** model (and any other models you want)

### Verification
```
User: "Regenerate the extension index"
Expected: Tool is invoked → report shows ✅ for each endpoint →
          files written confirmation → new data available for search
```

**Effort:** ~30 minutes

---

## Step 7E: Scheduled Regeneration

**Goal:** The index automatically refreshes on a schedule without any human interaction.

**Three options, pick based on your deployment:**

### Option A: Cron Inside Docker (Simplest)

Add to your `Dockerfile` or `entrypoint.sh`:

```dockerfile
# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Add cron job: regenerate index at 3 AM daily
RUN echo "0 3 * * * cd /app/backend && python generate_index.py --community --pages 2 >> /var/log/owui_index.log 2>&1" \
    | crontab -

# Start cron in background (add to your entrypoint)
# CMD cron && <your existing start command>
```

### Option B: Host-Level Cron (If Not Using Docker)

```bash
# crontab -e
0 3 * * * cd /path/to/project && /path/to/.venv/bin/python generate_index.py --community --pages 2 >> /var/log/owui_index.log 2>&1
```

### Option C: Systemd Timer (Production Linux)

```ini
# /etc/systemd/system/owui-index.service
[Unit]
Description=Regenerate OWUI Extension Index

[Service]
Type=oneshot
WorkingDirectory=/path/to/project
ExecStart=/path/to/.venv/bin/python generate_index.py --community --pages 2
EnvironmentFile=/path/to/project/.env
```

```ini
# /etc/systemd/system/owui-index.timer
[Unit]
Description=Daily OWUI Index Regeneration

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now owui-index.timer
```

### Recommendation
For your setup (Docker on Hugging Face Spaces), **Option A** is the right call. But since HF Spaces may restart containers, the Tool-based regeneration from Step 7D is your primary mechanism, and cron is a bonus.

**Effort:** ~15 minutes

---

## Bonus: GitHub Repos Collector

**Goal:** Pull extension metadata from curated GitHub repos to catch tools/functions not listed on the community site.

**Deliverable:**
```
owui_index_generator/
└── collectors/
    └── github_repos.py
```

### Implementation Strategy

```python
"""
github_repos.py
Fetches README files from curated GitHub repos and extracts extension metadata.

Strategy:
  1. Use GitHub API (no auth needed for public repos, 60 req/hr rate limit)
  2. Fetch raw README.md from each repo
  3. Parse for Markdown tables or structured lists of tools/functions
  4. Extract: name, description, file URL
  5. Return as list of CommunityExtension objects
"""

import re
import requests
from typing import Optional


CURATED_REPOS = [
    {
        "owner": "open-webui",
        "repo": "functions",
        "label": "Official Curated Functions",
        "type": "function",
    },
    {
        "owner": "open-webui",
        "repo": "pipelines",
        "label": "Official Pipelines",
        "type": "pipeline",
    },
    {
        "owner": "Haervwe",
        "repo": "open-webui-tools",
        "label": "Haervwe's Toolkit",
        "type": "tool",
    },
    {
        "owner": "owndev",
        "repo": "Open-WebUI-Functions",
        "label": "OwnDev Enterprise Functions",
        "type": "function",
    },
    {
        "owner": "Fu-Jie",
        "repo": "openwebui-extensions",
        "label": "Prompt Plus Suite",
        "type": "function",
    },
]


class GitHubCollector:
    def __init__(self, token: Optional[str] = None):
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"token {token}"
        self.session.headers["Accept"] = "application/vnd.github.v3+json"

    def fetch_repo_contents(self, owner: str, repo: str) -> list[dict]:
        """List files in the repo root."""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/"
        resp = self.session.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return []

    def fetch_python_files(self, owner: str, repo: str) -> list[dict]:
        """Find all .py files (non-recursive, root level)."""
        contents = self.fetch_repo_contents(owner, repo)
        py_files = []
        for item in contents:
            if item.get("name", "").endswith(".py"):
                py_files.append({
                    "name": item["name"].replace(".py", "").replace("_", " ").title(),
                    "filename": item["name"],
                    "url": item.get("html_url", ""),
                    "raw_url": item.get("download_url", ""),
                    "size": item.get("size", 0),
                })
        return py_files

    def extract_metadata_from_file(self, raw_url: str) -> dict:
        """
        Download a .py file and extract the docstring metadata block.
        Open WebUI tools/functions use a triple-quoted header with:
          title, author, description, version, etc.
        """
        try:
            resp = self.session.get(raw_url, timeout=10)
            content = resp.text[:2000]  # Only need the header

            metadata = {}
            # Match patterns like: title: Some Title
            for field in ["title", "author", "description", "version"]:
                match = re.search(
                    rf'{field}:\s*(.+?)$', content, re.MULTILINE | re.IGNORECASE
                )
                if match:
                    metadata[field] = match.group(1).strip().strip('"\'')

            return metadata
        except Exception:
            return {}

    def collect_all(self) -> list[dict]:
        """Collect extensions from all curated repos."""
        all_extensions = []

        for repo_info in CURATED_REPOS:
            owner = repo_info["owner"]
            repo = repo_info["repo"]
            label = repo_info["label"]
            ext_type = repo_info["type"]

            print(f"  📦 Scanning {owner}/{repo}...")

            py_files = self.fetch_python_files(owner, repo)

            for pf in py_files:
                meta = self.extract_metadata_from_file(pf["raw_url"])

                all_extensions.append({
                    "type": ext_type,
                    "name": meta.get("title", pf["name"]),
                    "slug": pf["filename"].replace(".py", ""),
                    "description": meta.get("description", f"From {label}"),
                    "author": meta.get("author", owner),
                    "url": pf["url"],
                    "downloads": 0,  # GitHub doesn't track this
                    "source": f"github:{owner}/{repo}",
                })

            print(f"    Found {len(py_files)} Python files")

        return all_extensions
```

### Integration with `generate_index.py`
Add a `--github` flag to the orchestrator:

```python
if args.github:
    from owui_index_generator.collectors.github_repos import GitHubCollector
    gh = GitHubCollector(token=os.getenv("GITHUB_TOKEN"))
    github_extensions = gh.collect_all()
    index_data["github_extensions"] = github_extensions
    print(f"📦 GitHub: {len(github_extensions)} extensions found")
```

**Effort:** ~1 hour (including rate limit handling and testing)

---

## Updated File Tree After Stage 2

```
owui-index-generator/
├── generate_index.py                    # Main orchestrator (updated)
├── owui_index_generator/
│   ├── __init__.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── local_api.py                 # ✅ Done (Stage 1)
│   │   ├── community_scraper.py         # ✅ Done (Stage 1)
│   │   └── github_repos.py             # 🆕 Step Bonus
│   ├── schema/
│   │   ├── __init__.py
│   │   └── extension.py                 # ✅ Done (Stage 1)
│   ├── renderers/
│   │   ├── __init__.py
│   │   └── markdown.py                  # ✅ Done (Stage 1)
│   ├── uploaders/
│   │   ├── __init__.py
│   │   └── knowledge_sync.py           # 🆕 Step 7A
│   ├── tools/
│   │   ├── extension_search.py          # 🆕 Step 7B (paste into OWUI)
│   │   └── index_regenerator.py         # 🆕 Step 7D (paste into OWUI)
│   └── templates/
│       └── index.md.j2                  # ✅ Done (Stage 1)
├── data/
│   ├── owui_index.json                  # Generated output
│   └── OWUI_INDEX.md                    # Generated output
├── config.yaml                          # Future: externalized config
├── .env                                 # API keys (gitignored)
├── .env.example
├── requirements.txt
├── SCRIPTS_INDEX.md                     # ✅ Done
└── BUILD_LOG.md                         # ✅ Done
```

---

## Execution Timeline

| Session | Steps | Time | Outcome |
|---------|-------|------|---------|
| **Session 1** | 7A (Knowledge Sync) + 7B (Search Tool) | ~75 min | Index is in RAG, search works in chat |
| **Session 2** | 7C (Advisor Model) + 7D (Regenerator Tool) | ~50 min | Full advisor experience working end-to-end |
| **Session 3** | 7E (Cron) + Bonus (GitHub collector) | ~75 min | Self-maintaining system with expanded catalog |

---

## Pre-Drafted Build Log Entries

Add these as you complete each step:

```markdown
### [TIMESTAMP] - Step 7A: Knowledge Base Ingestion
- **Status**: Completed
- **Changes**:
    - Built `owui_index_generator/uploaders/knowledge_sync.py`.
    - Created "OWUI Extension Index" Knowledge collection via API.
    - Verified RAG retrieval with test query.
- **Target**: Local

### [TIMESTAMP] - Step 7B: Extension Search Tool
- **Status**: Completed
- **Changes**:
    - Built `extension_search.py` Tool with `search_extensions` and `get_index_summary`.
    - Installed in Open WebUI, configured Valves.
    - Tested with [model name] — tool invocation confirmed.
- **Target**: Local, Open WebUI

### [TIMESTAMP] - Step 7C: Extension Advisor Model
- **Status**: Completed
- **Changes**:
    - Created "Extension Advisor" model preset.
    - Attached Knowledge collection + Extension Search Tool.
    - Ran 5-point verification test suite — all passed.
- **Target**: Open WebUI

### [TIMESTAMP] - Step 7D: Index Regeneration Tool
- **Status**: Completed
- **Changes**:
    - Built `index_regenerator.py` Tool.
    - Tested in-chat regeneration — JSON and MD files updated.
- **Target**: Local, Open WebUI
```

---

## Success Criteria

You'll know Stage 2 is complete when you can do this in a single chat session:

```
You:     "What tools do we have for web search?"
Advisor: [invokes search_extensions] "Here are 3 matching tools..."

You:     "Install the top one"
Advisor: "Go to Workspace → Tools → Import → paste this URL: ..."

You:     "Now refresh the index so it shows as installed"
Advisor: [invokes regenerate_index] "Done — index updated, now showing 1 installed tool"

You:     "Confirm it's there"
Advisor: [invokes search_extensions] "✅ SearXNG Tool — Status: Installed"
```

That's a fully self-aware, self-maintaining extension management system running inside your Open WebUI instance.