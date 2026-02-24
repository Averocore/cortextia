#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Path resolution for Host vs Container
# Container: /app/backend/data (set via ENV DATA_DIR in Dockerfile)
# Host: repo_root / data
DEFAULT_DATA_DIR = os.getenv("DATA_DIR", str(Path(__file__).resolve().parent / "data"))
DATA_DIR = Path(DEFAULT_DATA_DIR)
ARTIFACTS_DIR = DATA_DIR / "artifacts"
LOCK_PATH = DATA_DIR / ".sync_index.lock"
INDEX_JSON = DATA_DIR / "owui_index.json"
INDEX_MD = DATA_DIR / "OWUI_INDEX.md"

EXIT_OK = 0
EXIT_REGEN_FAIL = 1
EXIT_VALIDATION_FAIL = 2
EXIT_KNOWLEDGE_FAIL = 3

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

def acquire_lock() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        # atomic create
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()}\nstarted={utc_now_iso()}\n")
    except FileExistsError:
        # Check if process is still running (container specific, but helps host too)
        # Note: In container environments, stale locks are common on restart.
        # For simplicity in this stage, we just fail and let the operator clear it.
        raise RuntimeError(f"Lock already exists: {LOCK_PATH}. Another sync may be running or a previous run crashed. Please remove the lock file manually if you are sure no other sync is running.")

def release_lock() -> None:
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass

def run_cmd(cmd: list[str], env: dict[str, str], cwd: str | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8")
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    return proc.returncode, stdout, stderr

def load_index_json() -> dict:
    return json.loads(INDEX_JSON.read_text(encoding="utf-8"))

def validate_index(max_age_minutes: int = 15) -> tuple[bool, str, dict]:
    if not INDEX_JSON.exists():
        return False, f"Missing {INDEX_JSON}", {}
    try:
        idx = load_index_json()
    except Exception as e:
        return False, f"JSON parse failed: {e}", {}

    generated_at = idx.get("generated_at") or idx.get("generatedAt")
    if not generated_at:
        return False, "Missing generated_at in index JSON", idx

    try:
        ga_str = generated_at.replace("Z", "+00:00")
        ga_dt = datetime.fromisoformat(ga_str)
    except Exception as e:
        return False, f"Invalid generated_at format: {generated_at} ({e})", idx

    age_sec = (datetime.now(timezone.utc) - ga_dt.astimezone(timezone.utc)).total_seconds()
    if age_sec > max_age_minutes * 60:
        return False, f"Index too old: generated_at={generated_at} age={age_sec:.0f}s", idx

    # Category counts sanity check
    # Check if we have at least SOME models/tools/functions (common indicator of success)
    models = len(idx.get("models", []))
    tools_inst = len(idx.get("tools_installed", []))
    funcs_inst = len(idx.get("functions_installed", []))
    
    if models == 0 and tools_inst == 0 and funcs_inst == 0:
        return False, "Index contains zero local items; likely a failed API crawl", idx

    return True, "OK", idx

def main():
    load_dotenv()
    repo_root = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Stage 3A OWUI Index Sync Orchestrator")
    parser.add_argument("--profile", choices=["nightly", "weekly", "monthly"], required=True)
    default_base = os.getenv("OWUI_BASE_URL") or os.getenv("WEBUI_URL") or "http://localhost:7860"
    parser.add_argument("--base-url", default=default_base)
    parser.add_argument("--no-community", action="store_true")
    parser.add_argument("--skip-knowledge-sync", action="store_true")
    parser.add_argument("--pages-nightly", type=int, default=1)
    parser.add_argument("--pages-weekly", type=int, default=5)
    parser.add_argument("--pages-monthly", type=int, default=15)
    parser.add_argument("--validate-age-minutes", type=int, default=15)
    args = parser.parse_args()

    pages = {"nightly": args.pages_nightly, "weekly": args.pages_weekly, "monthly": args.pages_monthly}[args.profile]

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    artifact = {
        "run_started": utc_now_iso(),
        "profile": args.profile,
        "base_url": args.base_url,
        "community_enabled": (not args.no_community),
        "community_pages": (0 if args.no_community else pages),
        "status": "in_progress",
        "errors": [],
    }

    try:
        acquire_lock()

        env = os.environ.copy()
        env["OWUI_BASE_URL"] = args.base_url
        env["DATA_DIR"] = str(DATA_DIR)

        # 1) Regenerate
        # In container: /app/backend/data/generate_index.py
        # Host: same dir as this script
        gen_script = repo_root / "generate_index.py"
        
        cmd = [sys.executable, str(gen_script)]
        cmd += ["--output-dir", str(DATA_DIR)]
        if not args.no_community:
            cmd += ["--community", "--pages", str(pages)]

        print(f"Running regen: {' '.join(cmd)}")
        rc, out, err = run_cmd(cmd, env=env, cwd=str(repo_root))
        artifact["regen_returncode"] = rc
        artifact["regen_stdout_tail"] = out[-2000:]
        artifact["regen_stderr_tail"] = err[-2000:]

        if rc != 0:
            artifact["status"] = "regen_failed"
            artifact["errors"].append(f"Index regeneration failed with exit code {rc}")
            print(f"Regen failed: {err}")
            sys.exit(EXIT_REGEN_FAIL)

        # 2) Validate
        ok, msg, idx = validate_index(max_age_minutes=args.validate_age_minutes)
        artifact["validation_ok"] = ok
        artifact["validation_message"] = msg

        if not ok:
            artifact["status"] = "validation_failed"
            artifact["errors"].append(msg)
            print(f"Validation failed: {msg}")
            sys.exit(EXIT_VALIDATION_FAIL)

        # 3) Knowledge sync
        if not args.skip_knowledge_sync:
            # Run as module to ensure proper import context
            cmd = [sys.executable, "-m", "owui_index_generator.uploaders.knowledge_sync"]
            print(f"Running knowledge sync: {' '.join(cmd)}")
            rc, out, err = run_cmd(cmd, env=env, cwd=str(repo_root))
            artifact["knowledge_sync_returncode"] = rc
            artifact["knowledge_sync_stdout_tail"] = out[-2000:]
            artifact["knowledge_sync_stderr_tail"] = err[-2000:]

            if rc != 0:
                artifact["status"] = "knowledge_sync_failed"
                artifact["errors"].append(f"Knowledge sync failed with exit code {rc}")
                print(f"Knowledge sync failed: {err}")
                sys.exit(EXIT_KNOWLEDGE_FAIL)

        artifact["status"] = "completed"
        print("Sync completed successfully.")
        sys.exit(EXIT_OK)

    except SystemExit as e:
        code = int(e.code) if isinstance(e.code, int) and not isinstance(e.code, bool) else (1 if e.code else 0)
        _finish_artifact(artifact, code, args.profile)
        sys.exit(code)

    except Exception as e:
        artifact["status"] = "failed_unhandled"
        artifact["errors"].append(str(e))
        print(f"Unhandled failure: {e}")
        _finish_artifact(artifact, 1, args.profile)
        sys.exit(1)

    finally:
        release_lock()

def _finish_artifact(artifact, code, profile):
    artifact["run_finished"] = utc_now_iso()
    artifact["exit_code"] = code

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    artifact_path = ARTIFACTS_DIR / f"index_sync_{profile}_{ts}.json"
    
    # Add counts to artifact for visibility
    if INDEX_JSON.exists():
        try:
            idx = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
            artifact["counts"] = {
                "models": len(idx.get("models", [])),
                "tools_installed": len(idx.get("tools_installed", [])),
                "functions_installed": len(idx.get("functions_installed", [])),
                "prompts": len(idx.get("prompts", [])),
                "community_tools": len(idx.get("tools_available", [])),
                "community_functions": len(idx.get("functions_available", []))
            }
        except:
            pass

    artifact_json = json.dumps(artifact, indent=2)
    atomic_write_text(artifact_path, artifact_json)
    atomic_write_text(ARTIFACTS_DIR / "index_sync_last.json", artifact_json)

if __name__ == "__main__":
    main()
