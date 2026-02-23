---
description: Run final checks and update documentation when a session is finished.
---

# "Done For Now" Workflow

This workflow is triggered when the USER says "we are done for now". It ensures the codebase is healthy, documented, and fully synchronized.

## Step 1: Automated Script Indexing
// turbo
1. Scan the project for new `.py` or `.ps1` files.
2. If new scripts are found, update `SCRIPTS_INDEX.md` with descriptions derived from file headers.

## Step 2: Documentation Sync
// turbo
1. Check if the `generate_index.py` logic has changed.
2. If logic changed, run `python generate_index.py --community --pages 2` to ensure the live index matches the latest code.
3. Verify `README.md` reflects any new CLI arguments or capability changes.

## Step 3: Health Check
// turbo
1. Run `.\run_local.ps1` to ensure the container still boots with the latest code.
2. Verify `owui_index.json` is valid and non-empty.

## Step 4: Final Deployment
// turbo
1. Execute the `/deploy-changes` workflow to push everything to Hugging Face and GitHub mirrors.
2. Update `BUILD_LOG.md` with a "Session Summary" entry.
