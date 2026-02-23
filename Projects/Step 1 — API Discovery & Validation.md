# 🚀 Step 1 — API Discovery & Validation

The first move is the **highest priority, lowest effort** item: confirm what your Open WebUI instance actually exposes via its API, so everything we build downstream rests on verified ground truth.

---

## 🔬 Step 1: Enable Swagger & Map All API Endpoints

### 1A. Enable Developer Mode
In your Open WebUI Docker setup, ensure the environment variable is set:

```bash
# docker-compose.yml
environment:
  - ENV=dev
```
Or if running directly:
```bash
docker run -e ENV=dev ...
```
Then restart the container. This unlocks the interactive Swagger docs.

### 1B. Access Swagger UI
Navigate to:
```
http://<your-instance>:8080/docs
```
You should see a full interactive API explorer.

### 1C. Obtain Your API Key
1. Open WebUI → **Settings** → **Account**
2. Scroll to **API Keys**
3. Click **Create New Secret Key**
4. Save it — you'll need it for every subsequent step

### 1D. Validate Each Critical Endpoint
Run these `curl` commands (or use Swagger's "Try it out") and **save the raw JSON responses** for schema analysis:

```bash
export OWUI_URL="http://localhost:8080"
export API_KEY="sk-your-key-here"

# Models
curl -s -H "Authorization: Bearer $API_KEY" \
  "$OWUI_URL/api/models" | python3 -m json.tool > samples/models.json

# Tools
curl -s -H "Authorization: Bearer $API_KEY" \
  "$OWUI_URL/api/v1/tools" | python3 -m json.tool > samples/tools.json

# Functions (Pipes, Filters, Actions)
curl -s -H "Authorization: Bearer $API_KEY" \
  "$OWUI_URL/api/v1/functions" | python3 -m json.tool > samples/functions.json

# Prompts
curl -s -H "Authorization: Bearer $API_KEY" \
  "$OWUI_URL/api/prompts" | python3 -m json.tool > samples/prompts.json

# Knowledge bases
curl -s -H "Authorization: Bearer $API_KEY" \
  "$OWUI_URL/api/v1/knowledge" | python3 -m json.tool > samples/knowledge.json

# Config (for version info)
curl -s -H "Authorization: Bearer $API_KEY" \
  "$OWUI_URL/api/config" | python3 -m json.tool > samples/config.json
```

### 1E. Document What You Find
Create a quick reference file from your findings:

```markdown
# API_DISCOVERY.md

## Instance Info
- URL: http://localhost:8080
- Version: (from /api/config)
- Swagger: http://localhost:8080/docs

## Endpoint Status
| Endpoint               | Status | Sample Fields Returned                     |
|------------------------|--------|--------------------------------------------|
| GET /api/models        | ✅/❌  | id, name, info.description, ...            |
| GET /api/v1/tools      | ✅/❌  | id, name, meta.description, content, ...   |
| GET /api/v1/functions  | ✅/❌  | id, name, type, meta.description, ...      |
| GET /api/prompts       | ✅/❌  | command, title, content, ...               |
| GET /api/v1/knowledge  | ✅/❌  | id, name, description, data, ...           |
| GET /api/config        | ✅/❌  | version, ...                               |

## Key Observations
- [ ] Does `functions` response include a `type` field (pipe/filter/action)?
- [ ] Does `tools` response include `meta.manifest` or tags?
- [ ] Does `models` differentiate Ollama vs OpenAI vs custom?
- [ ] Are there pagination params needed for large result sets?
- [ ] Any undocumented endpoints discovered in Swagger?
```

---

## 🎯 What This Unlocks

| Finding | Impacts |
|---|---|
| Exact JSON field names & nesting | Pydantic schema design (Step 4) |
| Which fields carry descriptions/tags | How rich the index entries will be |
| Presence of `type` field in functions | Whether we can auto-classify Pipe/Filter/Action |
| Pagination behavior | Whether the collector needs looping logic |
| Undocumented endpoints | Possible bonus data sources (e.g., installed pipelines, MCP config) |

---

## ⏱️ Estimated Time
**15–30 minutes** — this is deliberately a quick win.

---

## ✅ Definition of Done
You have:
- [ ] Swagger UI accessible at `/docs`
- [ ] API Key generated and stored securely
- [ ] All 6 sample JSON files saved in a `samples/` folder
- [ ] `API_DISCOVERY.md` filled out with field mappings and observations
- [ ] A clear picture of any gaps (missing fields, broken endpoints, auth issues)

---

## 👉 What Comes Immediately After

Once you hand me back the **sample JSON outputs** (or even just the field names/structure), I can:

1. **Design the exact Pydantic schemas** (Step 4) tailored to your real data
2. **Write `local_api.py`** (Step 2) with confidence about parsing logic
3. Start both in parallel since the schema work removes all guesswork

Want me to draft the `curl` commands as a single shell script you can just run and pipe everything into a zip?