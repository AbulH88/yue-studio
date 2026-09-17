# YuE Studio — WSL Training Bridge Design

## Goal

Connect the existing YuE Studio Windows interface to the verified YuE2 instrumental AR LoRA workflow in Ubuntu/WSL2. A user must be able to select an imported instrumental dataset, validate the local training setup, start an isolated training run, and watch its progress without modifying the preserved trainer or successful `medieval_echoes` checkpoints.

This is the first integration milestone. Public installation, checkpoint conversion, generation, and vocal-song training remain separate later milestones.

## Chosen approach

Add a safe bridge layer between YuE Studio and the Mothersuperior-derived trainer. The bridge stages each run in its own workspace, records a complete manifest, invokes parameterized preparation and training commands through WSL, and exposes status and logs through the existing local HTTP API.

The trainer's model architecture and optimization behavior remain unchanged. The application will not run the existing scripts directly against their hardcoded shared `/workspace/real` paths because that could mix datasets or overwrite preserved state.

## Supported workflow

The first version supports instrumental datasets only.

- Use the dataset selected in the current project UI.
- Require one caption sidecar for every audio track.
- Treat every song as `[instrumental]`; vocal separation and lyric alignment are not run.
- Use the verified AR LoRA defaults: rank 64, learning rate `6e-5`, artist fraction `1.0`, cursor-loss weight `0.08`, BF16, and two-step gradient accumulation.
- Allow the user to choose the number of steps.
- Keep regularizer mixing disabled.

## Components

### Settings screen

Add a small Settings screen for machine-specific values:

- WSL distribution name.
- WSL Python executable.
- Trainer directory.
- YuE2 base-model directory.
- MERT directory.
- YuE2 VAE directory.
- Tokenizer-head checkpoint.
- Root directory for new run workspaces.

Settings are stored in the ignored local configuration file and are never committed to Git. No personal Windows or Linux path is used as a source-code default.

The screen includes a **Test Connection** action. It checks WSL availability, the selected distribution, Python, CUDA/PyTorch, the trainer script, required models and checkpoint, the run-workspace directory, and usable disk space. Results are returned as individual pass/fail checks with actionable messages.

### WSL bridge

Create a focused backend module responsible for:

- Safely constructing WSL argument arrays without shell interpolation.
- Translating Windows dataset paths with `wslpath` where needed.
- Running preflight commands with timeouts.
- Starting one preparation or training process at a time.
- Capturing stdout and stderr without blocking the web server.
- Tracking process state and an explicit stop request.

The bridge accepts structured settings and returns structured results. UI code does not construct shell commands.

### Isolated run workspace

Each Start Training action creates a unique run identifier and a separate Linux workspace below the configured run root. It contains:

```text
<run-id>/
  manifest.json
  source/
  prep/
  ar/
  checkpoints/
  logs/
```

Source audio and captions are staged into `source/`. Supported input formats are converted to the format required by preparation while preserving the original files. Filenames are normalized and collision-checked. Existing directories are never reused silently.

`manifest.json` is written before preparation begins. It records the run ID, timestamps, source dataset and file list, file sizes, relevant script hashes, configured model paths, all training parameters, generated commands, output paths, and current status. Later status changes are written atomically.

### Parameterized preparation and training

Add project-owned runner scripts that preserve the verified preparation and AR-training behavior while accepting explicit paths for source data, prepared features, generated `dataset.pt`, base models, tokenizer head, and output checkpoints.

The preparation stage:

1. Validates readable audio and non-empty captions.
2. Converts/stages tracks without changing originals.
3. Extracts the MERT and VAE data needed by the existing workflow.
4. Builds an artist-only AR dataset for the selected tracks.

The training stage runs the verified AR LoRA configuration with `artist_frac=1.0`. It does not read or write the preserved `/workspace/tok/full/medieval_echoes_only_raw` directory.

### Training API and UI

Add local API endpoints to:

- Read and save training settings.
- Run the preflight check.
- Start a training run.
- Read current run status and accumulated log events.
- Request that the active process stop cleanly.

The Training Runs screen displays:

- Current stage: validating, staging, preparing, training, completed, failed, or stopped.
- Current step and total steps.
- Latest loss, evaluation values, elapsed time, and reported VRAM.
- A readable live log.
- Failure details and the retained run directory.
- Discovered checkpoints belonging to that run.

The browser polls the local API for this first version. A WebSocket or server-sent event layer is unnecessary until polling proves inadequate.

## Data flow

```text
selected UI dataset
  -> Windows validation
  -> preflight WSL and CUDA checks
  -> unique manifest and run workspace
  -> staged/converted instrumental audio and captions
  -> MERT/VAE preparation
  -> artist-only AR dataset.pt
  -> verified AR LoRA training
  -> run-scoped logs and .pt checkpoints
  -> Training Runs display
```

## Error handling and safety

- Start Training is rejected when no dataset is selected, a caption is missing, configuration is invalid, CUDA is unavailable, required files are absent, another run is active, or disk space is insufficient.
- Validation failures identify the exact setting or track that needs attention.
- A failed preparation stage never starts training.
- Commands use argument arrays and validated paths rather than user-controlled shell strings.
- Logs and manifests are retained for failed and stopped runs.
- Stop first sends a normal termination request and reports whether the process ended; it does not delete the run directory.
- The preserved trainer copy, original audio, original captions, old WSL datasets, and successful checkpoints are never overwritten or deleted.
- YuE Studio never silently falls back to AI Toolkit.

## Verification

Automated backend tests cover configuration validation, Windows-to-WSL path handling, manifest creation, command construction, training-log parsing, status transitions, and rejection of conflicting runs. Subprocesses are mocked in unit tests.

Manual integration verification uses a short instrumental test run:

1. Save settings and pass every preflight check.
2. Select a small captioned dataset.
3. Start a short run and confirm the unique workspace and manifest exist before GPU work begins.
4. Confirm preparation and training logs appear in the UI.
5. Confirm step, loss, elapsed time, VRAM, and checkpoint discovery update correctly.
6. Stop one test run and verify its files and logs remain intact.
7. Complete one test run and confirm its creator-format `.pt` checkpoints remain isolated from all earlier runs.

## Acceptance criteria

1. A configured user can test the WSL/CUDA/trainer connection from YuE Studio.
2. Starting a run uses the dataset selected in the UI rather than a pre-existing hardcoded WSL dataset.
3. Every run has an isolated directory and a complete manifest written before preparation or training.
4. The UI reports preparation and training progress with live logs.
5. Checkpoints are discovered only from the active run's output directory.
6. Missing dependencies or invalid data fail safely with an actionable message.
7. Original datasets, preserved scripts, and successful historical checkpoints are unchanged.

## Deferred work

- Automated installation of WSL, CUDA, Python packages, models, and trainer assets.
- Creator `.pt` to ComfyUI `.safetensors` conversion and export.
- Generate/Test and listening-comparison workflows.
- Vocal datasets, lyrics, Demucs, and cursor alignment.
- Concurrent training runs and remote machines.
