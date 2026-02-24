# GitHub Issues for OWUI Index Generator Fixes

## [REG-01] Fix install URL prefix for community functions
**Type**: Bug | **Priority**: High
**Problem**: Both tools and functions currently use the same URL prefix (`/t/`), leading to 404s when attempting to install functions which must use `/f/`.
**Proposed Change**: Update `regenerate_index` to use `prefix = "t" if ext_type == "tools" else "f"`.
**Acceptance Criteria**: Community function `install_url` starts with `https://openwebui.com/f/`.
**Test Plan**: `test_regenerate_index_integration` verifies correct mapping in `owui_index.json`.

---

## [REG-02] Fix community API query string literal (`&type=` not HTML entity)

**Type**: Reliability | **Priority**: High

**Problem**: Community catalog fetch may use an HTML-escaped query delimiter (e.g., `&amp;type=`) instead of a literal `&type=`. If `&amp;` appears in the actual request URL, the server may treat it as a literal string, causing filtering to fail and resulting in incorrect or empty community results.

**Proposed Change**:
- Ensure the community API request URL is constructed using a literal ampersand:
  - `.../posts/search?page={page}&type={tool|function}`
- Do not include HTML entities (e.g., `&amp;`) in runtime request strings.

**Acceptance Criteria**:
- Outgoing requests for community crawl contain `&type=tool` and `&type=function` as literal query parameters.
- No outgoing request URL contains the substring `&amp;type=`.

**Test Plan**:
- Add/extend a unit test that intercepts the requested URL (via `responses` or monkeypatch) and asserts:
  - URL includes `&type=function` when fetching functions.
  - URL includes `&type=tool` when fetching tools.
  - URL does **not** contain `&amp;type=`.

---

## [REG-03] Support env var fallback for API key
**Type**: Security | **Priority**: Medium
**Problem**: Requiring the key in UI Valves is less secure than environment variables.
**Proposed Change**: Implement `_get_api_key` with fallback to `WEBUI_API_KEY`.
**Acceptance Criteria**: Tool runs successfully if Valve is empty but env var is set.
**Test Plan**: `test_api_key_env_fallback`.

---

## [REG-04] Atomic writes for outputs
**Type**: Reliability | **Priority**: High
**Problem**: Direct writes can result in corrupted files if the process is interrupted or multi-access occurs.
**Proposed Change**: Use `os.replace` after writing to a `.tmp` file.
**Acceptance Criteria**: `owui_index.json` is never partial.
**Test Plan**: `test_atomic_write`.

---

## [REG-05] Truncate + sanitize community description (deterministic + tested)

**Type**: Performance | **Priority**: Medium

**Problem**: Community item descriptions sourced from upstream content may contain excessive length and formatting (newlines/whitespace), causing index bloat and degrading search performance. Without deterministic sanitization, `owui_index.json` can grow rapidly and become slower to load/scan.

**Proposed Change**:
- Implement deterministic sanitization for community item descriptions during ingestion:
  - Normalize whitespace (strip leading/trailing whitespace).
  - Replace internal newlines (`\n`, `\r`) with spaces.
  - Collapse multiple spaces to single spaces (optional but recommended).
  - Truncate to a configurable `description_limit` (default: 500 chars).
- Store only the sanitized snippet in `description` (do not store full raw content unless explicitly required elsewhere).

**Acceptance Criteria**:
- Each community item `description`:
  - contains no `\n` or `\r`
  - has length `<= description_limit`
  - is stable/deterministic for the same upstream content
- Regeneration output size does not balloon due to unbounded descriptions.

**Test Plan**:
- Add a unit test that feeds a mocked community response with:
  - multi-line content
  - excessive length (e.g., >2000 chars)
- Assert in the resulting `owui_index.json` structure:
  - `description` has no newline characters
  - `len(description) <= description_limit`
  - `description` begins with expected normalized prefix (sanity check)

---

## [REG-06] Deduplicate community items across pages
**Type**: Bug | **Priority**: Medium
**Problem**: Paginating APIs can return duplicates if items move between pages during crawl.
**Proposed Change**: Use `seen_ids` set during collection.
**Acceptance Criteria**: No duplicate slugs in `owui_index.json`.
**Test Plan**: Integration test with mocked duplicate responses.

---

## [REG-07] Add retry/backoff for community API
**Type**: Reliability | **Priority**: High
**Problem**: Transient network issues or rate limiting (429) can fail the whole regeneration.
**Proposed Change**: Implement 3-attempt exponential backoff.
**Acceptance Criteria**: Single failures don't stop the job.
**Test Plan**: `test_fetch_community_retry`.

---

## [REG-08] Performance: Use Session + bounded concurrency for local API fetch (non-flaky)

**Type**: Performance | **Priority**: High

**Problem**: Sequential local API requests add unnecessary latency (total time becomes sum of endpoint latencies). Additionally, creating a new connection per request increases overhead. This slows index regeneration and increases the chance of timeouts under load.

**Proposed Change**:
- Use a single `requests.Session()` for all HTTP calls to reuse connections.
- Fetch local Open WebUI endpoints concurrently using `ThreadPoolExecutor` with bounded parallelism:
  - `max_workers` must be conservative (recommended: 3–5).
- Maintain existing timeouts and ensure failures degrade gracefully (a failing endpoint yields an empty list + report entry; job continues).

**Acceptance Criteria** (deterministic):
- Code uses a shared `requests.Session` object (not per-request `requests.get`) for local fetches.
- Local endpoint fetch is implemented via concurrency (executor/futures) with `max_workers <= 5`.
- If one local endpoint fails, regeneration still completes and writes index files successfully with that section empty and a failure noted in the report.

**Test Plan**:
- Add/extend a unit/integration test that:
  - Mocks local endpoints with controlled responses
  - Confirms all endpoints are requested (exact count)
  - Confirms regeneration completes even if one endpoint returns an error
- (Optional) Add a non-CI benchmark script if you want runtime performance measurement, but do not enforce strict time thresholds in CI.

---

## [REG-09] Compact JSON dump option (explicit behavior + verified output)

**Type**: Performance | **Priority**: Low

**Problem**: Pretty-printed JSON (indentation + spaces) increases file size and write time. This can slow regeneration and index loading, especially as the catalog grows.

**Proposed Change**:
- Add a `compact_json: bool` valve (default: False) controlling JSON serialization:
  - If `compact_json=True`, write JSON with:
    - `separators=(",", ":")`
    - `ensure_ascii=False`
    - no indentation
  - If `compact_json=False`, retain readable formatting (indent=2).
- Keep output schema identical regardless of formatting.

**Acceptance Criteria**:
- When `compact_json=True`:
  - `owui_index.json` contains no indentation-based formatting from `indent=2`
  - output uses compact separators (no spaces after `:` or `,`)
- When `compact_json=False`:
  - output remains pretty-printed (indentation/newlines present)
- Search tool can load and use the JSON in both modes.

**Test Plan**:
- Add a unit test that runs regeneration twice into a temp directory:
  1) `compact_json=False` → assert file contains newlines and indentation patterns
  2) `compact_json=True` → assert file contains minimal whitespace (e.g., no `": "` patterns)
- In both cases, parse JSON successfully and verify required top-level keys exist.

---

## [SRCH-01] Improve error visibility when loading index
**Type**: Reliability | **Priority**: Medium
**Problem**: Silent loading failures make debugging "empty results" impossible.
**Proposed Change**: Surface `File not found` or `JSON error` to UI.
**Acceptance Criteria**: Error text appears in chat if load fails.
**Test Plan**: `test_error_visibility`.

---

## [SRCH-02] Normalize author formatting
**Type**: UI | **Priority**: Low
**Problem**: Inconsistent `@` prefixes result in `@@user` or `user` without link.
**Proposed Change**: Standardize on `lstrip("@")` followed by forced `@{author}` formatting.
**Acceptance Criteria**: UI consistently shows `@username`.
**Test Plan**: `test_author_normalization`.

---

## [SRCH-03] Fix description ellipsis
**Type**: UI | **Priority**: Low
**Problem**: Ellipsis appended to short descriptions looks broken.
**Proposed Change**: Only append if length exceeded.
**Acceptance Criteria**: Short descriptions end with their actual punctuation.
**Test Plan**: `test_ellipsis_logic`.

---

## [SRCH-04] Sorting tie-break improvement
**Type**: Feature | **Priority**: Medium
**Problem**: Users expect their installed tools to rank higher than distant community matches.
**Proposed Change**: Add `priority` field (Installed=2, Model/Prompt=1, Community=0) to sort key.
**Acceptance Criteria**: Installed tools appear first on score ties.
**Test Plan**: `test_search_installed_priority`.

---

## [SRCH-05] Extend search coverage to models/prompts
**Type**: Feature | **Priority**: High
**Problem**: Searcher currently ignores models and prompts.
**Proposed Change**: Add search loops for `models` and `prompts` keys.
**Acceptance Criteria**: Searching "GPT" or "/command" returns results.
**Test Plan**: `test_search_models_prompts`.
