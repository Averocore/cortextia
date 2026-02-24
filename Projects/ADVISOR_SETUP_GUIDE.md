# 🤖 Extension Advisor Integration Guide

This guide explains how to integrate the **Extension Index** into your Open WebUI instance. We use automation for the data layer and a specialized agent for the user interface.

> **Public-safe note:** This document contains no secrets, internal URLs, or tokens. Do not paste sensitive values into documentation or chat.

## Step 1: Scheduled Sync (Primary Operating Mode)

In production, you should run a container-native scheduler (like **supercronic**) that performs:
1) `regenerate_index()` (writes `owui_index.json` + `OWUI_INDEX.md` to disk)
2) **Sanity checks**: Verifies file existence, JSON structure, and freshness.
3) `knowledge_sync.py`: Updates the "OWUI Extension Index" Knowledge collection.
4) **Artifact logging**: Writes detailed run results to `artifacts/`.

**Orchestrator Role:**
- `sync_index.py` is the **canonical orchestrator**. It should be the ONLY way automated background refreshes happen.
- The Advisor Agent's `regenerate_index` tool is for **on-demand user refreshes**. It updates files on disk but does *not* automatically re-upload to Knowledge.
- **Strict Policy**: The Advisor should NEVER trigger `sync_index.py` automatically; only the orchestrator or an admin should run Knowledge Sync.

### Important: Index Files vs Knowledge Base
- **Index Files**: `owui_index.json` (for search) and `OWUI_INDEX.md` (for human reading).
- **Knowledge Base**: The RAG collection the AI reads. 
- **Drift Warning**: If you regenerate the index files manually via Tool B, but do not run `knowledge_sync.py`, the Agent's *search tool* will be fresh, but its *Knowledge Base context* will be stale.

## Step 2: Install the Tools (Search + Summary + Regenerate)

The Advisor uses two Tools (two Python files). Open WebUI automatically detects callable methods in the `Tools` class.

### ✅ Callable Verification Checklist
After pasting the code for each Tool, verify that the **Callables** list in the Open WebUI interface precisely matches these names. If they differ, the System Prompt will fail.

- [ ] `search_extensions`
- [ ] `get_index_summary`
- [ ] `regenerate_index`

*Note: Open WebUI may also expose non‑callable attributes as UI entries — only the above three should be treated as valid callables for the System Prompt.*

### Tool A — Extension Catalog Search
**Source file:** `owui_index_generator/tools/extension_search.py`

**Callables exposed:**
- `search_extensions(query, category=None)` — searches installed + community catalog and returns user-facing Markdown results.
- `get_index_summary()` — returns a summary including last generation time, file sizes, and item counts.

**Official Extension Taxonomy:**
| Category | Scope |
| :--- | :--- |
| `models` | Local LLMs (Ollama, OpenRouter, OpenAI compatible) |
| `tools` | Installed Python tools (Tools UI) |
| `functions` | Installed Python functions (Functions UI) |
| `prompts` | Prompt templates (prompts/custom entries) |
| `community_tools` | Available for download at openwebui.com |
| `community_functions` | Available for download at openwebui.com |

**Deterministic Rules:** These categories represent the canonical index schema. The indexer assigns categories based on the entity’s origin (local vs community) and its declared type in the API.

**Valves:**
- `index_path` (default: `/app/backend/data/owui_index.json`)
- `max_results` (default: 10)

---

### Tool B — Index Regenerator
**Source file:** `owui_index_generator/tools/index_regenerator.py`

**Callable exposed:**
- `regenerate_index()` — re-queries local APIs and optionally the community catalog, then writes updated files.

**Valves:**
- `owui_base_url` (default: `http://localhost:7860`)
- `api_key` (optional if using env fallback)
- `output_dir` (default: `/app/backend/data`)
- `include_community` (default: true)
- `community_pages` (default: 1)
- `compact_json` (default: false)
- `description_limit` (default: 500)

**Security / Secret Handling:**
- Recommended: set `WEBUI_API_KEY` as an environment secret in your backend.
- If `WEBUI_API_KEY` is present, you do not need to store the key in Tool Valves.

---

## Community Integration Notes (Important)

- **URL Structures**: Community install links differ by type:
  - Tools use `https://openwebui.com/t/author/slug`
  - Functions use `https://openwebui.com/f/author/slug`
- **Literal Query Strings**: When calling the community API, ensure query strings remain literal (e.g., `&type=tool`). Avoid HTML-escaped entities like `&amp;type=...` in actual HTTP requests.
- **Resiliency**: Community API availability is not guaranteed. Failures in community fetch must not block local index regeneration.

---

## Environment Variable Mapping

The system uses the following environment variables for configuration:
- **Scripts/Orchestrator**: `OWUI_BASE_URL` (local API target), `WEBUI_API_KEY` (authentication).
- **Tool Valves**: `owui_base_url` (overrides default host), `api_key` (overrides environment secret if set).

## Step 3: Create the Extension Advisor Agent
1.  Go to **Workspace > Models > Create a Model**.
2.  **Name**: `Extension Advisor`
3.  **Base Model**: Select a reasoning model (GPT-4o, Claude 3.5, or similar).
4.  **Knowledge**: Attach the **OWUI Extension Index** collection.
5.  **Tools**: Attach both **Extension Catalog Search** AND **Index Regenerator**.
6.  **System Prompt**: Use the full prompt provided below.

---

## 📝 The Advisor System Prompt (Optimized)

```markdown
You are the **Extension Advisor** for this Open WebUI instance.

You help users discover, evaluate, and install Open WebUI extensions using the local Extension Index.

## You have access to:
- Knowledge Base: **OWUI Extension Index**
- Tools (ONLY these callables):
  - `search_extensions` — returns user-facing Markdown search results
  - `get_index_summary` — returns a Markdown summary table + Last generated timestamp
  - `regenerate_index` — regenerates index artifacts on disk

## Rules
- **Non-Hallucination**: Do NOT invent extensions, capabilities, or links. Use ONLY tool output or the Knowledge Base.
- **Byte-Preserving Output**: NEVER rewrite, shorten, expand, re-interpret, or restructure tool-generated Markdown. Output must be exactly as returned by the tool.
- **Rank Integrity**: Do NOT reorder results. Keep the order returned by `search_extensions` as it reflects relevance scoring.
- **No Formatting Corrections**: Do NOT fix, clean up, normalize, reorganize, or “repair” Markdown returned by tools — even if it contains errors.
- **Tool Output Boundary Rule**: When printing tool-generated Markdown, output it as a standalone block with no additional text inserted before, inside, between, or immediately after lines of the block. Add any commentary only AFTER the complete tool output, separated by a blank line and a heading like “Next step” or “Notes”.
- **Header Invariance**: Preserve the header lines returned by `search_extensions` exactly (e.g., `## 🔍 Search Results for: "..."`). Do not rename, paraphrase, or re-title them.
- **Secrets**: Do NOT ask for or repeat secrets (API keys/tokens/passwords).
- **Security Warning Deduplication**: If tool output already includes a security warning, do NOT repeat it. If tool output does NOT include a security warning and you recommend installation, add exactly one warning line:
  > ⚠️ Security: Extensions execute arbitrary Python code on the server. Install only from trusted sources and review code before importing.
- **Resiliency Policy (Community vs Local)**: Community API availability is not guaranteed. If community fetch fails during `regenerate_index` but local endpoints succeed, treat the run as partial success. Report local success and community failure separately and provide next steps (retry later, reduce `community_pages`, or disable `include_community`).

## Overview Requests
If the user asks “what do we have?” or “overview”:
1) Call `get_index_summary`.
2) Print the returned Markdown exactly as-is.
3) Add 2–6 bullet points interpreting the totals and freshness. Do not invent categories. **Interpret only numeric totals and timestamps — do not infer trends, gaps, or missing items.**
4) Offer next actions (search by capability or regenerate).

## Capability Requests
If the user asks for a capability (“web search”, “RAG”, “voice”, “automation”):
1) Call `search_extensions` with the user’s query.
2) Print the returned Markdown exactly as-is (standalone block; no interleaving commentary).
3) After the block, add a short heading (e.g., “Next step”) and ask ONE follow-up question: “Which one do you want to install?”

## Refresh Requests
If the user asks to refresh/update/sync:
1) Call `regenerate_index`.
2) Summarize success/failure and next steps.
3) Note: Manual regeneration updates the search index immediately, but the Knowledge Base (RAG) updates separately via the automated `sync_index.py` process.
4) **Warning**: If users rely heavily on RAG-based summaries, stale Knowledge may cause the Advisor to answer with outdated descriptions despite fresh search results.
5) If community fetch fails but local regeneration succeeds, treat it as partial success and explain how to retry community later (reduce `community_pages` or disable `include_community`).
```

## Output Contract (API Specification)

**1. `get_index_summary()`**

*   **Returns**: Markdown String
*   **Content**:
    *   Host info (`instance_url`)
    *   Freshness (`generated_at` timestamp)
    *   Pipe table with columns: `Category`, `Count`
    *   Total items summary

**2. `search_extensions(query, category=None)`**

*   **Returns**: Markdown String
*   **Content**:
    *   Header: `## 🔍 Search Results for: "..."` (The header format must remain unchanged so the Advisor can rely on it for tool-output boundary detection).
    *   Results Block: List of items including Title, Type, Status, Description, and Action link.
    *   Footer: Multi-line security warning.
    *   Advisor must not duplicate the tool’s security warning footer.

**3. `regenerate_index()`**

*   **Returns**: Markdown String
*   **Content**:
    *   Start/Finish timestamps.
    *   Success/Failure status per local endpoint.
    *   Page-by-page community fetch status.
    *   Final file paths updated.

---

## Troubleshooting & Error Matrix

| Symptom | Probable Cause | Fix |
| :--- | :--- | :--- |
| Search returns "Index not found" | `regenerate_index` has never run. | Run `regenerate_index` or trigger `sync_index.py`. |
| Search results don't match chat context | Knowledge search vs Tool search drift. | Check if Knowledge Sync has run since last regen. |
| Regeneration succeeds but search still returns stale results | Operator misconfig in path. | Confirm `index_path` valve matches `output_dir` + filename. |
| `get_index_summary` returns outdated timestamps even after regeneration | Disk write failure or wrong mount. | Ensure the backend user has write permissions and `output_dir` points to the correct directory. |
| Community fetch fails but local endpoints succeeded | Community API unavailable / rate-limited. | Treat as partial success. Retry later, reduce `community_pages`, or disable `include_community`. |
| Community links use `/t/` for functions | Non-deterministic URL logic. | Verify Tool A code handles prefix matching correctly. |
| Regenerator fails with 401 | Invalid or missing API Key. | Check `WEBUI_API_KEY` environment variable. |
| Knowledge Sync creates duplicates | Missing existing collection lookup. | Verify `knowledge_sync.py` implements "find before create." |

## Operator Recommendations (Defaults)

*   `community_pages`: **1** for normal use; **5–15** for deep initial crawls. *Note: Increasing beyond 10 will significantly slow regeneration and may cause rate limiting.*
*   `include_community`: **true** for maximum advisor utility; **false** for air-gapped or internal-only environments.
*   `compact_json`: **true** if file size or write speed becomes a priority; **false** (default) for human-readable audit logs.
*   `description_limit`: **500** is a good balance for RAG context and visual layout.

---

## Version Drift and Rebuild Safety

To protect against breaking updates and data inconsistency, follow these operational rules:

*   **Major Schema Changes**: When the generator schema changes (new fields, category renames), operators should delete the old `owui_index.json` before regenerating to ensure a clean state.
*   **Regenerator Code Updates**: If the regenerator logic changes (e.g., new fields, altered item structure), operators must force a full rebuild by deleting both `owui_index.json` and `OWUI_INDEX.md` before running the new version.
*   **Knowledge Inconsistency**: If the Knowledge Sync results in inconsistent RAG documents, delete the existing collection in Open WebUI and allow `sync_index.py` to recreate it.
*   **Callable Updates**: If tool callable names are changed in the Python code, the Advisor system prompt MUST be updated immediately to reflect the new API.

---

*Generated by <https://github.com/Averocore/cortextia>*
