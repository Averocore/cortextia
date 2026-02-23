# Build & Deployment Log

This log tracks all changes, builds, and deployments for the Cortextia project.

## Log Entry Schema
- **Timestamp**: ISO 8601
- **Status**: (Planned | In Progress | Completed | Failed)
- **Changes**: Summary of modifications
- **Target**: (Local | Hugging Face | GitHub)
- **Artifacts**: Linked screenshots/logs if applicable

---

## Log History

### [2026-02-21T13:46:00Z] - Project Hardening and Mirroring
- **Status**: Completed
- **Changes**: 
    - Fixed `ValueError` by adding required environment variables to `Dockerfile`.
    - Set up GitHub mirror at `Averocore/cortextia`.
    - Added `.gitignore` to prevent secret leaks.
    - Added local development environment helper files (`.env.example`, `run_local.ps1`).
- **Target**: Local, Hugging Face, GitHub
- **Artifacts**: [Deployment Verification Screenshot](C:\Users\Jawad\.gemini\antigravity\brain\9ca46e8c-daa2-4d7b-b954-961ea3c6b272\cortextia_running_1771671212981.png)

### [2026-02-21T13:50:00Z] - Logging & Workflow Initialization
- **Status**: Completed
- **Changes**: 
    - Initialized `BUILD_LOG.md`.
    - Created `.agent/workflows/deploy-changes.md` to enforce the "log-before-and-after" policy.
- **Target**: Local, Hugging Face, GitHub

### [2026-02-21T13:52:00Z] - Customizing WebUI Name (Workflow Test)
- **Status**: Completed
- **Changes**: 
    - Changed `WEBUI_NAME` in `Dockerfile` to "Cortextia AI".
    - Verified the `deploy-changes` workflow enforcement.
    - Confirmed naming change live on Hugging Face Space.
- **Target**: Local, Hugging Face, GitHub

### [2026-02-22T12:45:00Z] - WebUI Customization & Master Plan Review
- **Status**: Completed
- **Changes**: 
    - Formalized "Master Plan" and "Step 1" documentation in `/Projects`.
    - Added `ENV=dev` and developer flags to `Dockerfile` for API access.
    - Created `test_api.py` for automated API endpoint discovery.
    - Installed Python dependencies (`requests`, `python-dotenv`) on host.
- **Target**: Local, Documentation
- **References**: `Projects/Master Plan/`, `Projects/Step 1 — API Discovery & Validation.md`

### [2026-02-22T15:42:00Z] - Security Hardening: Removing Hardcoded Secrets
- **Status**: Completed
- **Changes**: 
    - Removed `WEBUI_SECRET_KEY` from `Dockerfile`.
    - Pushed changes to GitHub and Hugging Face.
    - `WEBUI_SECRET_KEY` and `OPENAI_API_KEY` moved to Hugging Face Secrets UI.
- **Target**: Local, Hugging Face, GitHub

### [2026-02-22T16:00:00Z] - Local Docker Setup & First Boot
- **Status**: In Progress
- **Changes**: 
    - Fixed `run_local.ps1` to skip rebuild if image already exists.
    - Fixed duplicate `OPENAI_API_BASE_URL` in `Dockerfile`.
    - Added `static/` folder permissions to `Dockerfile` to resolve boot-time permission errors.
    - Configured `WEBUI_ADMIN_EMAIL` and `WEBUI_ADMIN_PASSWORD` in `.env` for auto-admin creation.
    - Set `ENABLE_SIGNUP=False` in `Dockerfile` to lock down public signups.
    - Wiped local `data/` folder to force fresh database initialization.
    - Container successfully started; embedding model (`all-MiniLM-L6-v2`, 931MB) downloading on first boot.
- **Pending**: 
    - Confirm login at `http://localhost:7860` with admin credentials.
    - Generate API Key from Settings → Account.
    - Add `WEBUI_API_KEY` to `.env` and run `test_api.py` to complete Step 1.
- **Target**: Local
- **Next Session**: Resume with Step 1 — API Discovery & Validation.
