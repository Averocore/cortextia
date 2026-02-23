### Next step: **Phase 3 — Automation + Coverage Expansion (make Stage 2 “hands-off”)**

You’ve got an advisor that can search + regenerate + sync to Knowledge *manually*. The next logical step is to make the system **self-refreshing and broader than the community API**, while keeping it reproducible/auditable.

---

## 1) Make a single “one-shot” sync command (foundation for scheduling)
**Goal:** One command that (a) regenerates index → (b) renders Markdown → (c) runs `knowledge_sync.py` → (d) writes an artifact log.

**Deliverable**
- `sync_index.py` (or a `generate_index.py --sync-knowledge` flag)

**Why this is next:** Scheduling/automation is pointless if the workflow is split into multiple manual commands and can drift.

**Acceptance criteria**
- Running one command updates:
  - `data/owui_index.json`
  - `data/OWUI_INDEX.md`
  - Knowledge collection updated (same collection ID, no duplicates)
  - A timestamped artifact file saved (see step 2)

---

## 2) Add “evidence artifacts” per run (auditability + debug)
**Goal:** Every sync produces a small, stable record you can diff later.

**Deliverables**
- `artifacts/` folder (or `data/artifacts/`)
- JSON file per run, e.g. `artifacts/index_sync_2026-02-23T19-10-00Z.json` containing:
  - generated_at
  - counts (models/tools/functions/community tools/community functions)
  - dedupe rule/version
  - community pages fetched
  - file sizes
  - knowledge collection id + file id

**Why:** This closes the last “trust gap” in your build log and makes regressions obvious.

---

## 3) Implement Step 7E: scheduled regeneration (with environment-appropriate strategy)
Pick one based on where you care most (Local Docker vs Hugging Face Space):

### If Local Docker is primary
- Add cron or systemd timer to run the one-shot sync nightly
- Suggested schedule:
  - Nightly: `--pages 2` (fast)
  - Weekly: “deep sync” `--pages 15` (slow, validates counts)

### If Hugging Face Space is primary
Cron inside Spaces can be fragile depending on restarts. Practical options:
- Run sync on container boot (entrypoint) + manual regenerator tool
- Optional: add a lightweight “daily sync” loop inside the app container (only if you’re comfortable running a background process)

**Acceptance criteria**
- Index updates without a human initiating it
- Knowledge base reflects new index automatically

---

## 4) Add Phase 3 coverage: GitHub curated collectors (Bonus item you deferred)
**Goal:** Catch high-value tools/functions not present (or not discoverable) via the community API.

**Deliverable**
- `collectors/github_repos.py` integrated behind `--github`
- Extend schema to store GitHub-sourced entries distinctly (so you don’t confuse them with community registry installs)

**Acceptance criteria**
- `OWUI_INDEX.md` gains a “Curated GitHub Catalog” section
- `extension_search.py` can optionally include/exclude GitHub results via `category`

---

## 5) (After automation) Expand taxonomy: Pipelines + MCP Servers + OpenAPI specs
Right now you have great coverage for: models/tools/functions/prompts/knowledge/community tools+functions.

Next additions depend on how you plan to *use* them:

- **Pipelines**: index from `open-webui/pipelines` repo + your local configured pipeline endpoints
- **MCP Servers**: maintain a `config.yaml` registry (local truth), because there usually isn’t a standard local API endpoint listing MCP servers
- **OpenAPI tools**: treat these like “external tool providers”; index by spec URL + base URL + auth notes

**Deliverable**
- `config.yaml` (authoritative list of MCP/pipeline/OpenAPI endpoints)
- generator reads config and renders them into the index

---

### What I’d do first (recommended order)
1) **One-shot sync command** (regen + markdown + knowledge sync)  
2) **Artifacts per run**  
3) **Scheduling (7E)**  
4) **GitHub collector**  
5) Pipelines/MCP/OpenAPI config-driven indexing

---

## Next step: Phase 3A — **Automate refresh (nightly/weekly/monthly) with one “one-shot sync” command**

You already have all the *capabilities* (generate index, search it, regen from UI, sync to Knowledge). Now you want it to become **hands-off** with a schedule that matches your cadence:

- **Fast**: nightly
- **Medium**: weekly
- **Deep**: monthly

### First: one command that does everything
Before scheduling anything, create a single orchestrator that:

1) regenerates `owui_index.json` + `OWUI_INDEX.md`  
2) syncs `OWUI_INDEX.md` into Knowledge (via `knowledge_sync.py`)  
3) writes a small artifact record (`artifacts/*.json`) with counts + run metadata

Call it one of:
- `sync_index.py` (recommended), or
- `generate_index.py --sync-knowledge --artifacts`

**Why this is next:** cron/systemd should call *one* command. Otherwise your scheduled jobs drift and become un-debuggable.

---

## Recommended schedule profiles (matches your intent)
You said: “fast nightly once a week” + “deep monthly”. That phrase is ambiguous, so here’s the clean schedule that usually fits what people actually want:

### A) Nightly “fast” (every day)
- `--pages 1` (or 2) for community tools/functions
- keeps recency high with minimal load

### B) Weekly “medium” (once a week)
- `--pages 5` (or similar)
- catches more of the long tail without a huge crawl

### C) Monthly “deep” (1st of month)
- `--pages 15+`
- used for validation, metrics, and “full catalog refresh”

If you truly meant “only run fast weekly (not nightly)”, tell me and I’ll collapse A→B. But I strongly recommend the 3-tier approach above.

---

## Concrete implementation plan (local Docker now, VPS later)

### Step 1 — Add `sync_index.py`
**CLI design:**
- `--profile nightly|weekly|monthly`
- profile controls `--pages` and any extra flags
- always runs:
  - `generate_index.py --community --pages N`
  - then `knowledge_sync.py`
  - then writes `artifacts/index_sync_<timestamp>.json`

**Acceptance test:**
- Run: `python sync_index.py --profile nightly`
- Confirm:
  - `data/owui_index.json` updated (`generated_at` changes)
  - `data/OWUI_INDEX.md` updated
  - Knowledge collection updated (no duplicates)
  - artifact JSON created

### Step 2 — Add artifact logging (for audit/debug)
Create `artifacts/` (or `data/artifacts/`) and write per-run JSON containing:
- timestamp, profile, pages
- counts (models/tools/functions/community tools/community functions)
- dedupe rule version (string)
- file sizes (md/json)
- knowledge collection id + uploaded file id
- success/failure + error message

This closes the “trust gap” permanently (you can prove what happened on any run).

---

## Scheduling (local now)

### Option 1 (recommended for Local Docker): **Host scheduler runs Python**
Run scheduled tasks on the host using your `.venv` and talk to Open WebUI at `http://localhost:7860`. Since your `data/` is a bind mount into the container, writing to `data/` on host updates `/app/backend/data` in-container automatically.

#### If you’re on Linux/macOS host (cron)
Example crontab:

```cron
# Nightly fast at 02:15
15 2 * * * cd /path/to/cortextia && /path/to/.venv/bin/python sync_index.py --profile nightly >> artifacts/cron.log 2>&1

# Weekly medium (Sunday) at 03:15
15 3 * * 0 cd /path/to/cortextia && /path/to/.venv/bin/python sync_index.py --profile weekly >> artifacts/cron.log 2>&1

# Monthly deep on the 1st at 04:15
15 4 1 * * cd /path/to/cortextia && /path/to/.venv/bin/python sync_index.py --profile monthly >> artifacts/cron.log 2>&1
```

#### If you’re on Windows host: Task Scheduler
Create three scheduled tasks that run:

- Program: `python`
- Args: `sync_index.py --profile nightly` (and weekly/monthly)

(If you want, I can give you exact `schtasks.exe` commands once you confirm your repo path and python path.)

---

## Scheduling (VPS later)

When you migrate to a VPS, do **systemd timers** on the host (very reliable). The exact same `sync_index.py --profile X` design carries over cleanly.

You’d add:
- `owui-index-sync.service` (oneshot)
- three timers (nightly/weekly/monthly), or one timer + profile logic

---

### Recommendation (Windows now, VPS later): **Use host Python for scheduling**
Given your repo/scripts live on the host and already run in a `.venv`, **host Python + Windows Task Scheduler** is the simplest and most reliable right now. It also maps cleanly to a VPS later (swap Task Scheduler → systemd timers; keep the same `sync_index.py`).

**Why not `docker exec` right now?**
- You’d need the scripts + deps inside the container image (or mount the whole repo), and ensure the container’s Python environment matches your `.venv`.
- Debugging scheduled `docker exec` tasks on Windows tends to be more annoying than just running the same host command you already use.

**One important caveat:** your repo is in **OneDrive**. OneDrive can occasionally lock files or delay writes. It usually works, but if you see flaky behavior, the best fix is to move the repo to a non-synced path (or at least put `data/` + `artifacts/` outside OneDrive and symlink them). Not required, just a stability note.

---

## Next step (concrete): add a one-shot sync entrypoint + schedule it

### Step A — Create a single command: `sync_index.py`
This script should do, in order:
1) run your generator (local + community) with a profile-based page depth  
2) render `OWUI_INDEX.md` (already part of your generator flow)  
3) run `knowledge_sync.py` to update the Knowledge collection  
4) write an `artifacts/index_sync_<timestamp>.json` summary

Profiles matching your requirement:
- **nightly (fast):** pages = 1 (or 2)
- **weekly (medium):** pages = 5
- **monthly (deep):** pages = 15 (or whatever you used for “Deep Community Sync”)

Once `sync_index.py` exists and works interactively, scheduling becomes trivial.

---

## Step B — Add PowerShell wrappers (best practice for Task Scheduler)
Create these files (so each scheduled task has a simple command and no tricky quoting):

**1) `scripts\sync_index_nightly.ps1`**
```powershell
$Repo = "C:\Users\Jawad\OneDrive - MSFT\Open WebUI"
Set-Location $Repo

# Load .env into process environment (skip comments/blank lines)
Get-Content "$Repo\.env" | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
  $name, $value = $_ -split '=', 2
  $value = $value.Trim().Trim('"')
  [System.Environment]::SetEnvironmentVariable($name.Trim(), $value, "Process")
}

& "$Repo\.venv\Scripts\python.exe" sync_index.py --profile nightly
```

**2) `scripts\sync_index_weekly.ps1`**
Same, just `--profile weekly`.

**3) `scripts\sync_index_monthly.ps1`**
Same, just `--profile monthly`.

This avoids embedding secrets in scheduled task definitions and keeps everything in repo.

---

## Step C — Create scheduled tasks (3 tasks)
Open an elevated PowerShell (or CMD) and run:

### Nightly (fast) at 02:15
```cmd
schtasks /Create /F /TN "Cortextia\OWUI Index Nightly" ^
  /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\Jawad\OneDrive - MSFT\Open WebUI\scripts\sync_index_nightly.ps1\"" ^
  /SC DAILY /ST 02:15
```

### Weekly (medium) Sunday at 03:15
```cmd
schtasks /Create /F /TN "Cortextia\OWUI Index Weekly" ^
  /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\Jawad\OneDrive - MSFT\Open WebUI\scripts\sync_index_weekly.ps1\"" ^
  /SC WEEKLY /D SUN /ST 03:15
```

### Monthly (deep) 1st of the month at 04:15
```cmd
schtasks /Create /F /TN "Cortextia\OWUI Index Monthly" ^
  /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\Jawad\OneDrive - MSFT\Open WebUI\scripts\sync_index_monthly.ps1\"" ^
  /SC MONTHLY /D 1 /ST 04:15
```

### Verify tasks exist
```cmd
schtasks /Query /TN "Cortextia\OWUI Index Nightly"
```

---

## What to verify after scheduling (quick)
1) Run each script manually once:
   - `.\scripts\sync_index_nightly.ps1`
2) Confirm files update:
   - `data\owui_index.json` → `generated_at` changes
   - `data\OWUI_INDEX.md` changes
   - `artifacts\index_sync_*.json` created
3) Confirm Knowledge got updated (same collection, new file version, no duplicates)

---

## When you migrate to a VPS later
You’ll keep the same `sync_index.py` and swap Task Scheduler → **systemd timers**. No redesign needed if you do host-run scheduling now.

---

### One question that affects the exact implementation
Do you already have a `.venv` folder inside `C:\Users\Jawad\OneDrive - MSFT\Open WebUI\`?

- If **yes**, the scripts above work as-is.
- If **no**, tell me where your venv/python lives (or if you’re using global Python), and I’ll adjust the wrapper scripts and `schtasks` commands accordingly.

Good—then the next step is to **implement the one-shot sync command** and wire it into **Windows Task Scheduler**.

Below is the exact “do-this-next” sequence.

---

## 1) Create `sync_index.py` (single entrypoint for scheduled runs)

Place this at your repo root (same level as `generate_index.py`).

```python
# sync_index.py
import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def file_size_bytes(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def safe_read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def count_community(index_data: dict) -> tuple[int, int, int]:
    community = index_data.get("community_extensions", []) or []
    total = len(community)
    tools = sum(1 for e in community if e.get("type") == "tool")
    functions = sum(1 for e in community if e.get("type") == "function")
    return total, tools, functions


def main():
    load_dotenv()  # loads .env from current working dir

    parser = argparse.ArgumentParser(description="One-shot OWUI index sync")
    parser.add_argument("--profile", choices=["nightly", "weekly", "monthly"], required=True)
    parser.add_argument("--base-url", default=os.getenv("OWUI_BASE_URL", "http://localhost:7860"))
    parser.add_argument("--pages-nightly", type=int, default=1)
    parser.add_argument("--pages-weekly", type=int, default=5)
    parser.add_argument("--pages-monthly", type=int, default=15)
    parser.add_argument("--no-community", action="store_true")
    parser.add_argument("--skip-knowledge-sync", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    data_dir = repo_root / "data"
    artifacts_dir = repo_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    pages = {
        "nightly": args.pages_nightly,
        "weekly": args.pages_weekly,
        "monthly": args.pages_monthly,
    }[args.profile]

    run_started = utc_now_iso()
    artifact = {
        "run_started": run_started,
        "profile": args.profile,
        "base_url": args.base_url,
        "community_enabled": (not args.no_community),
        "community_pages": pages if not args.no_community else 0,
        "status": "in_progress",
        "errors": [],
    }

    # 1) Generate index (local + optional community)
    try:
        cmd = ["python", str(repo_root / "generate_index.py")]
        if not args.no_community:
            cmd += ["--community", "--pages", str(pages)]

        proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
        artifact["generate_index_returncode"] = proc.returncode
        artifact["generate_index_stdout_tail"] = proc.stdout[-2000:]
        artifact["generate_index_stderr_tail"] = proc.stderr[-2000:]

        if proc.returncode != 0:
            raise RuntimeError(f"generate_index.py failed (rc={proc.returncode})")
    except Exception as e:
        artifact["errors"].append(f"generate_index: {e}")
        artifact["status"] = "failed"

    # 2) Knowledge sync (optional)
    if artifact["status"] != "failed" and not args.skip_knowledge_sync:
        try:
            # Run module to avoid path issues
            cmd = ["python", "-m", "owui_index_generator.uploaders.knowledge_sync"]
            proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
            artifact["knowledge_sync_returncode"] = proc.returncode
            artifact["knowledge_sync_stdout_tail"] = proc.stdout[-2000:]
            artifact["knowledge_sync_stderr_tail"] = proc.stderr[-2000:]

            if proc.returncode != 0:
                raise RuntimeError(f"knowledge_sync failed (rc={proc.returncode})")
        except Exception as e:
            artifact["errors"].append(f"knowledge_sync: {e}")
            artifact["status"] = "failed"

    # 3) Collect counts + sizes for artifact
    index_json = data_dir / "owui_index.json"
    index_md = data_dir / "OWUI_INDEX.md"
    idx = safe_read_json(index_json)

    community_total, community_tools, community_functions = count_community(idx)

    artifact["run_finished"] = utc_now_iso()
    artifact["counts"] = {
        "models": len(idx.get("models", []) or []),
        "tools_installed": len(idx.get("tools", []) or []),
        "functions_installed": len(idx.get("functions", []) or []),
        "prompts": len(idx.get("prompts", []) or []),
        "knowledge": len(idx.get("knowledge", []) or []),
        "community_total": community_total,
        "community_tools": community_tools,
        "community_functions": community_functions,
    }
    artifact["files"] = {
        "owui_index_json_bytes": file_size_bytes(index_json),
        "owui_index_md_bytes": file_size_bytes(index_md),
    }

    if artifact["status"] != "failed":
        artifact["status"] = "completed"

    # 4) Write artifact
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    artifact_path = artifacts_dir / f"index_sync_{args.profile}_{ts}.json"
    artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    # Also write a stable “last run” pointer
    (artifacts_dir / "index_sync_last.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    # Exit code
    raise SystemExit(0 if artifact["status"] == "completed" else 1)


if __name__ == "__main__":
    main()
```

### What this gives you
- One command per schedule profile:
  - `python sync_index.py --profile nightly`
  - `python sync_index.py --profile weekly`
  - `python sync_index.py --profile monthly`
- Always creates `artifacts/index_sync_<...>.json` so you can audit any run.

---

## 2) Add `/artifacts` to `.gitignore`
Artifacts are useful locally but shouldn’t bloat the repo:

```
artifacts/
```

(If you want to keep `index_sync_last.json` tracked, we can do a tighter ignore pattern; default is easiest.)

---

## 3) Create the PowerShell wrappers (Task Scheduler-friendly)

Create:

- `scripts\sync_index_nightly.ps1` runs: `.\.venv\Scripts\python.exe sync_index.py --profile nightly`
- `scripts\sync_index_weekly.ps1` runs: `... --profile weekly`
- `scripts\sync_index_monthly.ps1` runs: `... --profile monthly`

Use the wrapper pattern I gave earlier (loads `.env` + sets location). Since you confirmed `.venv` exists, it will work as-is.

---

## 4) Create the 3 scheduled tasks (Windows)

Run the `schtasks` commands from the earlier message (nightly/weekly/monthly).

---

## 5) Quick manual verification (before trusting scheduler)

Run each once in PowerShell from repo root:

```powershell
.\.venv\Scripts\python.exe sync_index.py --profile nightly
.\.venv\Scripts\python.exe sync_index.py --profile weekly
.\.venv\Scripts\python.exe sync_index.py --profile monthly
```

Check:
- `data\owui_index.json` updated
- `data\OWUI_INDEX.md` updated
- `artifacts\index_sync_last.json` exists and says `"status": "completed"`

---

With only `WEBUI_API_KEY` and `WEBUI_URL` set, you’re *almost* there. The only risk is that some of your scripts (especially `knowledge_sync.py` / collectors) may be looking for `OWUI_BASE_URL` (or similar) and will default to `http://localhost:7860`—which could mismatch if you ever change ports/host later.

## Minimal fix (recommended): add one alias env var
Add this to your `.env` (same value as `WEBUI_URL`):

```env
WEBUI_URL=http://localhost:7860
OWUI_BASE_URL=http://localhost:7860
WEBUI_API_KEY=xxxxx
```

That’s the fastest way to ensure **all components** (existing + future) can find the instance URL consistently.

## Better fix (code-hardening): support both names everywhere
Update any script that reads the base URL to fall back like this:

```python
base_url = (
    os.getenv("OWUI_BASE_URL")
    or os.getenv("WEBUI_URL")
    or "http://localhost:7860"
)
```

### Where to apply it
- `sync_index.py` (for `--base-url` default)
- `owui_index_generator/uploaders/knowledge_sync.py` (base URL resolution)
- any collector that has a base URL setting

## One more important tweak (prevents scheduler PATH issues)
In `sync_index.py`, when you spawn subprocesses, use the current venv interpreter instead of `"python"`:

```python
import sys
cmd = [sys.executable, str(repo_root / "generate_index.py"), ...]
cmd = [sys.executable, "-m", "owui_index_generator.uploaders.knowledge_sync"]
```

This prevents Task Scheduler runs from accidentally using global Python.

---

## What you should do next (in order)
1) Add `OWUI_BASE_URL` to `.env` (same as `WEBUI_URL`)
2) Patch `sync_index.py` to use `WEBUI_URL` fallback + `sys.executable`
3) Run manually once:
   ```powershell
   .\.venv\Scripts\python.exe sync_index.py --profile nightly
   ```
4) Only then create the 3 scheduled tasks.

