# Guided WSL Setup Implementation Plan

## 1. Setup state and safe command layer

- Add `yue_studio/setup_service.py` with a small persisted state model: idle, checking, needs-wsl, needs-restart, installing, downloading, verifying, ready, and failed.
- Keep machine-specific setup state in the ignored `studio.config.json`.
- Add a serialized worker, timestamped logs, and read-only status API. All WSL execution goes through a focused helper with safe argument lists and clear error text.
- Test state transitions and the rule that only one setup process is active.

## 2. Detection and app-owned environment

- Detect Windows WSL support, available distributions, selected Ubuntu, GPU/CUDA, and disk space.
- Reuse `TrainingBridge.autodetect()` and `TrainingBridge.preflight()` as the final definition of a ready machine.
- Create a stable app-owned Ubuntu environment and install apt/Python dependencies only after user starts setup.
- If WSL is unavailable, return the single Windows installation command and a restart-required state; do not attempt elevation or restart Windows.

## 3. Model manifest and installer

- Add a versioned manifest declaring required assets, destination paths, expected sizes, source URLs, and optional checksums.
- Add resumable, temporary-file downloads in WSL with pre-download disk checks and atomic completion.
- Report per-item progress to the UI. Detect a gated Hugging Face response and pause with a clear authentication instruction instead of handling credentials in the app.
- Do not overwrite detected existing models; adopt them when they pass validation.

## 4. HTTP API and setup UI

- Add setup endpoints for status, start, retry, and detailed logs.
- Make the first-run UI a simple setup checklist. Existing users see Ready or can open Advanced Setup.
- Keep native Windows file picker behavior for datasets and avoid browser-native dialogs.
- Preserve the existing Settings page as an advanced repair surface rather than removing it.

## 5. Verification and documentation

- Add unit tests for detector results, command creation, manifest validation, download-state parsing, gating, errors, and config preservation.
- Run Python compilation, all unit tests, JS syntax checks, and final `TrainingBridge.preflight()` against the current Ubuntu environment.
- Update the README with the normal user flow and the one explicit WSL administrator/restart exception.

## Delivery boundaries

The implementation will not run a real training job, delete existing environments/models/runs, add Docker, package an installer, or implement ComfyUI conversion.
