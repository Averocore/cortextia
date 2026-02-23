# 📋 Master Plan: Open WebUI Plugin/Extension Index Generator

## 🎯 Objective

Create a comprehensive, auto-generated Markdown index file (`OWUI_INDEX.md`) that catalogs all available and installed **Models, Tools, Functions (Pipes/Filters/Actions), Pipelines, Prompts, and MCP servers** with URLs, descriptions, and metadata — enabling an agent to recommend and facilitate installation of relevant extensions on demand.

---

## 🏗️ PHASE 1: Understand the Taxonomy

In Open WebUI, **Tools** allow LLMs to do things outside their default abilities (such as retrieving live info or performing custom tasks), while **Functions** help the WebUI itself do more things, like adding new AI models or creating smarter ways to filter data.

The index must cover these distinct extension types:

| Type | Sub-Type | Description | Source |
|---|---|---|---|
| **Tools** | Workspace Tools | Python scripts that extend LLM capabilities by providing them with functions to perform specific tasks such as web search, image generation, or API interactions. | `openwebui.com/tools`, GitHub repos |
| **Functions** | **Pipe** | A Pipe Function is how you create custom agents/models or integrations, which then appear in the interface as if they were standalone models. | `openwebui.com/functions` |
| **Functions** | **Filter** | A Filter Function tweaks data before it gets sent to the AI or after it comes back — Inlet adjusts input, Outlet modifies the output (cleaning up responses, adjusting tone, formatting, etc.). | `openwebui.com/functions` |
| **Functions** | **Action** | Adds custom UI buttons/actions to the chat interface. | `openwebui.com/functions` |
| **Pipelines** | — | Pipelines extend what Tools and Functions can do with even more flexibility, allowing you to turn features into OpenAI API-compatible formats. | `github.com/open-webui/pipelines` |
| **MCP Servers** | Native HTTP / MCPO Proxy | MCP is an open standard that allows LLMs to interact with external data and tools. Open WebUI can connect directly to any MCP server that exposes an HTTP/SSE endpoint, and use the MCPO Proxy to bridge stdio-based community MCP servers. | Various |
| **OpenAPI Tools** | — | Generic web servers that provide an OpenAPI (.json or .yaml) specification — Open WebUI can ingest these specs and treat every endpoint as a tool. | Various |
| **Models** | Ollama / OpenAI / Custom | Base and custom workspace models | Local instance + `openwebui.com/models` |
| **Prompts** | Templates | Prompt templates available via `GET /api/prompts`, enabling creation of reusable prompts across conversations. | Local instance + community |

---

## 🏗️ PHASE 2: Data Sources & Collection Strategy

### A. Community Registry (Remote — `openwebui.com`)
The community offers prompts, models, tools, functions, discussions and reviews — created by the community, available to everyone. Browse, install, contribute at openwebui.com.

| Source URL | What It Contains |
|---|---|
| `https://openwebui.com/tools` | All community-shared Tools |
| `https://openwebui.com/functions` | All community-shared Functions (Pipes, Filters, Actions) |
| `https://openwebui.com/models` | Community model presets and characters |
| `https://openwebui.com/prompts` | Community prompt templates |

**Collection Method:** Scrape or use API (if available) from `openwebui.com`. Each listing has: name, author (`@username`), description, download count, date, and a detail/import URL.

### B. Local Instance (Installed — via API)
The API provides essential information for integration and automation. Authentication is required via Bearer Token — obtain your API key from Settings > Account in the Open WebUI.

| API Endpoint | Data |
|---|---|
| `GET /api/models` | Fetches all models created or added via Open WebUI. |
| `GET /api/prompts` | Installed prompt templates |
| `GET /api/v1/tools` | Installed workspace tools |
| `GET /api/v1/functions` | Installed functions (Pipes, Filters, Actions) |
| `GET /api/v1/knowledge` | Knowledge bases / RAG collections |
| `GET /api/v1/files` | Uploaded files |

Open WebUI provides Swagger documentation to help developers understand and test API endpoints — but you must set `ENV=dev` for the Swagger docs to be accessible.

### C. Third-Party GitHub Repos (Curated)

| Repository | Focus |
|---|---|
| `github.com/open-webui/functions` — Curated custom functions approved by the Open WebUI core team. | Official functions |
| `github.com/Haervwe/open-webui-tools` — A modular toolkit with over 15 specialized tools, function pipelines, and filters. | Research, creativity, agentic |
| `github.com/owndev/Open-WebUI-Functions` — Custom pipelines, filters, and integrations for Azure AI, N8N, Google Gemini, etc. | Enterprise integrations |
| `github.com/Fu-Jie/openwebui-extensions` — Open WebUI Prompt Plus: an all-in-one prompt management suite. | Prompts, agents, artifacts |
| `github.com/open-webui/pipelines` | Official pipelines framework |

---

## 🏗️ PHASE 3: Index Schema (Markdown Structure)

The generated `OWUI_INDEX.md` file should use this structure:

```markdown
# 🗂️ Open WebUI Extension Index
> Auto-generated on: {{TIMESTAMP}}
> Instance: {{INSTANCE_URL}}
> Open WebUI Version: {{VERSION}}

## 📊 Summary
| Category       | Installed | Available (Community) |
|----------------|-----------|----------------------|
| Tools          | X         | Y                    |
| Functions      | X         | Y                    |
| ├─ Pipes       | X         | Y                    |
| ├─ Filters     | X         | Y                    |
| └─ Actions     | X         | Y                    |
| Models         | X         | Y                    |
| Prompts        | X         | Y                    |
| Pipelines      | X         | Y                    |
| MCP Servers    | X         | Y                    |
| Knowledge/RAG  | X         | —                    |

---

## 🔧 Tools

### Installed Tools
| Name | ID | Description | Author | Status | Source URL |
|------|----|-------------|--------|--------|------------|
| ...  | ...| ...         | ...    | ✅ Active / ⏸️ Inactive | ... |

### Available Community Tools (Not Installed)
| Name | Description | Author | Downloads | Tags | Install URL |
|------|-------------|--------|-----------|------|-------------|
| ...  | ...         | ...    | ...       | web-search, media, ... | https://openwebui.com/t/... |

---

## ⚙️ Functions

### Installed Functions
| Name | ID | Type (Pipe/Filter/Action) | Description | Global? | Assigned Models |
|------|----|---------------------------|-------------|---------|-----------------|
| ...  |... | ...                       | ...         | ✅/❌   | model-a, model-b |

### Available Community Functions (Not Installed)
| Name | Type | Description | Author | Downloads | Tags | Install URL |
|------|------|-------------|--------|-----------|------|-------------|
| ...  | Pipe | ...         | ...    | ...       | ...  | https://openwebui.com/f/... |

---

## 🤖 Models
| Name | ID | Provider | Type | Base Model | Tools Attached | Knowledge Attached |
|------|----|----------|------|------------|----------------|--------------------|
| ...  | ...| Ollama/OpenAI/Custom | ... | ... | tool-a, tool-b | kb-1 |

---

## 📝 Prompts
| Name | Command | Description | Author | Source |
|------|---------|-------------|--------|--------|
| ...  | /...    | ...         | ...    | Local / Community |

---

## 🔌 Pipelines & MCP Servers
| Name | Type | Endpoint | Description | Status |
|------|------|----------|-------------|--------|
| ...  | Pipeline / MCP-HTTP / MCP-MCPO | ... | ... | ✅/❌ |

---

## 🏷️ Tag Index (Cross-Reference)
| Tag              | Extensions                                      |
|------------------|--------------------------------------------------|
| web-search       | SearXNG Tool, Perplexica Pipe, DuckDuckGo Tool  |
| image-generation | DALL-E Tool, ComfyUI Tool, HF Image Gen         |
| code-execution   | Python Sandbox, gVisor Runner                    |
| voice/audio      | ElevenLabs TTS, Whisper STT                      |
| RAG              | RAG Pipeline, Knowledge Ingest                   |
| automation       | N8N Pipe, Home Assistant Pipe                    |
| ...              | ...                                               |
```

---

## 🏗️ PHASE 4: Generator Script Architecture

```
owui-index-generator/
├── generate_index.py          # Main orchestrator
├── collectors/
│   ├── local_api.py           # Hits /api/* endpoints on local instance
│   ├── community_scraper.py   # Scrapes openwebui.com/tools, /functions, /models
│   └── github_repos.py        # Parses curated GitHub repos' READMEs
├── schema/
│   └── extension.py           # Pydantic models for each extension type
├── renderers/
│   └── markdown.py            # Jinja2 template → OWUI_INDEX.md
├── templates/
│   └── index.md.j2            # The Markdown Jinja2 template
├── config.yaml                # Instance URL, API key ref, repo list, options
└── requirements.txt           # requests, beautifulsoup4, pydantic, jinja2, pyyaml
```

### Key Logic:

1. **`local_api.py`** — Authenticates with Bearer token, hits each endpoint, normalizes into schema objects
2. **`community_scraper.py`** — Fetches tool/function listing pages, extracts metadata (handle pagination, rate limiting)
3. **`github_repos.py`** — Clones/fetches README.md files, parses tables/lists for tool metadata
4. **`markdown.py`** — Merges all data, cross-references installed vs. available, renders via Jinja2 template
5. **Diffing** — Marks items as `✅ Installed`, `🆕 New`, `⬆️ Update Available` by comparing local vs. community

### Storage Location:
The local directory bound to `/app/data` within the container makes files directly available on the local computer.

Place the file at:
```
/app/backend/data/OWUI_INDEX.md       # Inside Docker container
```
Or equivalently in the host volume mapped to `/app/backend/data`.

---

## 🏗️ PHASE 5: Keeping It Fresh

| Strategy | Method |
|---|---|
| **Scheduled Regeneration** | Cron job or Celery task runs `generate_index.py` nightly |
| **Event-Driven Update** | Hook into Open WebUI's install/uninstall events (if possible via filter function) |
| **Manual Trigger** | An Open WebUI **Action Function** button that triggers regeneration |
| **Versioned History** | Git-commit each regeneration or timestamp-suffix old versions |

---

## 🏗️ PHASE 6: Agent Integration

Once the index exists, the agent can use it by:

1. **Loading `OWUI_INDEX.md` as a Knowledge Base** — Upload it to Open WebUI's RAG / Knowledge system so any model can reference it
2. **System Prompt Injection** — A Filter Function injects a summary of available extensions into the system prompt
3. **Tool-Based Lookup** — A dedicated **Tool** that reads the index and returns matching extensions for a user query
4. **Recommendation Logic** — When a user asks for a capability (e.g., "I need to search the web"), the agent checks the Tag Index, finds matching entries, and suggests install commands

---

## 🧾 SUGGESTED PROMPT

Use this prompt for an LLM agent (or as a system prompt for a dedicated "Extension Advisor" model in Open WebUI) to generate and maintain the index:

---

```markdown
# System Prompt: Open WebUI Extension Index Generator & Advisor

You are the **Open WebUI Extension Advisor**, an agent responsible for building,
maintaining, and consulting a comprehensive index of all available and installed
extensions for this Open WebUI instance.

## Your Responsibilities

### 1. INDEX GENERATION
When asked to generate or update the index, you will:

- **Query the local Open WebUI API** using these endpoints (authenticated via
  Bearer token stored in your environment):
  - `GET /api/models` — all installed/connected models
  - `GET /api/v1/tools` — all installed workspace tools  
  - `GET /api/v1/functions` — all installed functions (Pipes, Filters, Actions)
  - `GET /api/prompts` — all prompt templates
  - `GET /api/v1/knowledge` — all knowledge bases
  - `GET /api/v1/files` — all uploaded files

- **Scrape the Open WebUI Community site** for available (not yet installed)
  extensions:
  - https://openwebui.com/tools — community tools
  - https://openwebui.com/functions — community functions
  - https://openwebui.com/models — community model presets
  - https://openwebui.com/prompts — community prompts

- **Check curated GitHub repositories** for third-party extensions:
  - github.com/open-webui/functions (official curated)
  - github.com/open-webui/pipelines (official pipelines)
  - github.com/Haervwe/open-webui-tools
  - github.com/owndev/Open-WebUI-Functions
  - github.com/Fu-Jie/openwebui-extensions

- **Produce a unified Markdown file** (`OWUI_INDEX.md`) with the following
  sections: Summary Table, Tools (installed + available), Functions by type
  (installed + available), Models, Prompts, Pipelines & MCP Servers, and a
  cross-referencing Tag Index.

- For each entry, capture: **Name, ID/Slug, Type, Brief Description (≤2 sentences),
  Author, Source URL, Install URL, Status (Installed/Available/Update),
  Downloads (if known), Tags/Categories, Dependencies (API keys needed, etc.),
  Compatibility Notes**.

### 2. RECOMMENDATION
When a user describes a need, capability, or workflow:

- Search the index by tags, descriptions, and types.
- Recommend the **top 3-5 most relevant extensions** with:
  - Name and one-line description
  - Install method (community import URL or manual steps)
  - Any prerequisites (API keys, external services, model requirements)
  - Whether it's a Tool (LLM-invoked) vs. Function (WebUI-level) vs. Pipeline
- Warn about security considerations per Open WebUI's guidance:
  "Only install from trusted sources. Review code before importing."
- If no existing extension matches, suggest how one could be built.

### 3. INSTALLATION GUIDANCE  
When the user wants to install an extension:

- For community extensions: Provide the direct import URL pattern:
  `https://openwebui.com/t/{author}/{tool-slug}` (tools) or
  `https://openwebui.com/f/{author}/{function-slug}` (functions)
- Walk through: Navigate to Workspace > Tools/Functions > Import > paste URL
- For GitHub-sourced extensions: Provide the raw .py file URL and explain
  the copy-paste-into-editor method
- Note any Valves (configuration settings) that need to be set post-install

### 4. COMPATIBILITY AWARENESS
- Flag if a tool requires **Native function calling mode** (needs capable models
  like GPT-4o, Claude, Qwen 3 32B+, Llama 3.3 70B+)
- Note if a tool works in **Default mode** (prompt-engineering based, works with
  any model)
- Indicate when a Pipeline is needed instead of a Tool/Function (for heavy
  processing, custom dependencies, or separate-server execution)

## Important Security Note
Always remind users: Extensions execute arbitrary Python code on the server.
Only install from trusted sources. Review code before importing.

## Output Format
When generating the index, output valid Markdown suitable for saving as
`OWUI_INDEX.md`. When making recommendations, use clear structured responses
with comparison tables where helpful.

## Environment
- Instance URL: {{INSTANCE_URL}}
- API Key: {{API_KEY}} (use for authenticated API calls)
- Data Directory: /app/backend/data/
- Index File Path: /app/backend/data/OWUI_INDEX.md
```

---

## ✅ Implementation Checklist

| # | Step | Priority | Effort |
|---|------|----------|--------|
| 1 | Enable `ENV=dev` and explore Swagger docs to confirm all API endpoints | 🔴 High | Low |
| 2 | Write `local_api.py` collector — test against your instance | 🔴 High | Medium |
| 3 | Write `community_scraper.py` — scrape openwebui.com listings | 🔴 High | Medium |
| 4 | Define Pydantic schema for unified extension entries | 🟡 Medium | Low |
| 5 | Build Jinja2 template for `OWUI_INDEX.md` | 🟡 Medium | Low |
| 6 | Wire up `generate_index.py` orchestrator | 🟡 Medium | Medium |
| 7 | Upload generated index to Open WebUI as a Knowledge document | 🟡 Medium | Low |
| 8 | Create an "Extension Advisor" model with the system prompt above | 🟢 Nice | Low |
| 9 | Build a custom **Tool** that reads the index and answers queries | 🟢 Nice | Medium |
| 10 | Set up cron/scheduled regeneration | 🟢 Nice | Low |
| 11 | Build an **Action Function** for one-click regeneration from chat UI | 🟢 Nice | Medium |

---

This plan gives you a self-updating knowledge base that turns your Open WebUI instance into a self-aware system — the agent can introspect what's installed, what's available, and intelligently bridge the gap based on whatever the user needs next.