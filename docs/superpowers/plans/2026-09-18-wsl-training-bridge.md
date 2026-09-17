# WSL Training Bridge Implementation Plan

## Scope

Implement the approved first milestone: local settings, WSL/CUDA preflight, isolated instrumental run creation, dataset staging/preparation, AR LoRA launch, live status/log polling, stop support, and run-scoped checkpoint discovery.

Checkpoint conversion, generation, vocal training, and public dependency installation are excluded.

## Work sequence

1. Extract WSL process, validation, manifest, status, and log parsing behavior into `yue_studio/training_bridge.py`.
2. Add project-owned parameterized WSL scripts under `yue_studio/wsl/` for instrumental preparation and AR training. Preserve the verified model, LoRA targets, optimizer, schedule, and checkpoint behavior while replacing hardcoded data/output paths with explicit arguments.
3. Extend the local API in `yue_studio/app.py` with settings, preflight, run start, run status, run listing, and stop endpoints.
4. Add Settings and Training Runs panels to the existing UI. Wire saving, connection testing, starting, polling, log display, progress, checkpoint display, and stopping.
5. Add unit tests for command construction, safe names, manifest creation, log parsing, state transitions, and validation failures using mocked subprocesses.
6. Run unit tests, Python compilation, JavaScript syntax validation, and a read-only real-machine preflight. Do not start a GPU training run automatically.
7. Update the README with setup and first-run instructions, then commit the implementation.

## Safety checks

- Never write to `/workspace/tok/full/medieval_echoes_only_raw`.
- Refuse an existing run directory.
- Write the manifest before staging or GPU work.
- Use `subprocess` argument lists; pass run configuration through JSON rather than interpolated shell commands.
- Keep source audio/captions unchanged.
- Allow only one active run per YuE Studio process.
- Retain failed/stopped run artifacts and logs.
