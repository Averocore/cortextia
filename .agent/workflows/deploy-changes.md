---
description: Deploy changes to Hugging Face and GitHub mirrors
---

# Deploy Changes Workflow

This workflow MUST be followed for every deployment or significant code change. It enforces the "Update-Before-Change" and "Update-After-Change" logging policy.

## Step 1: Initialize Log Entry
Before making any changes to `Dockerfile`, `README.md`, or project configuration:
1. Open `BUILD_LOG.md`.
2. Add a new entry with the current timestamp.
3. Set **Status** to `In Progress`.
4. Describe the **Planned Changes**.

## Step 2: Implementation & Local Validation
// turbo
1. Execute the code changes.
2. Run `.\run_local.ps1` to verify the build passes locally.
3. Verify functionality at `http://localhost:7860`.

## Step 3: Deployment
// turbo
1. Stage changes: `git add .`
2. Commit: `git commit -m "..."`
3. Push to production: `git push origin main`
4. Push to mirror: `git push github main`

## Step 4: Finalize Log Entry
After the changes are pushed and verified on Hugging Face:
1. Re-open `BUILD_LOG.md`.
2. Update the **Status** to `Completed`.
3. Add any final notes, observed behaviors, or artifact links (screenshots).
4. Save and commit the log update.
