# YuE Studio — Local Windows App Design

## Goal

Build a standalone local Windows application for training and testing YuE2 instrumental LoRAs. The app provides a polished medieval creator-studio interface while keeping all audio, models, captions, checkpoints, and exports local.

## Product scope

The first release supports:

- Project creation and local project folders.
- Audio-folder import with waveform previews.
- Automatic instrumental dataset captioning on import.
- Caption review, editing, and validation before training.
- A YuE2 Instrumental LoRA training preset.
- WSL2 trainer execution with live logs, progress, GPU, and VRAM status.
- Checkpoint listing, loss graphs, generated sample previews, and A/B comparison.
- Conversion of creator-format checkpoints to ComfyUI-compatible `.safetensors`.
- User-selectable export destinations, with `./exports/` as the default.
- Optional copy/export to a configured ComfyUI LoRA folder.

The app must not hardcode the user's current `G:\` paths.

## Recommended architecture

Use a local web application packaged with a Windows launcher:

- Python backend for filesystem operations, WSL2 process control, trainer integration, checkpoint conversion, and configuration.
- React/Vite frontend for the dashboard UI.
- A local HTTP API bound to localhost only.
- A Windows launcher that starts the backend and opens the browser UI.
- A project-local configuration file plus a safe `.env.example` for GitHub.

This keeps the interface easy to iterate while retaining a simple Windows installation path.

## Main screens

### Projects

Create/open a project such as `Medieval Echoes`. Store project metadata, dataset references, training runs, samples, and exports under the project directory.

### Dataset

Import WAV/FLAC/MP3 files, display duration and waveform, analyze each track with a general-purpose local music captioner, and allow manual caption edits. The default caption engine is ACE-Step Captioner GGUF through a local llama.cpp-compatible service. OpenRouter audio models may be added as an opt-in provider later; they are never required for local use.

The caption pipeline keeps both the raw audio description and the final YuE2 caption. A deterministic formatter extracts genre, subgenre, instrumentation, vocal state, mood, tempo, arrangement, and production traits. Project trigger words are optional and configurable; the app must not force medieval tags onto unrelated projects.

Validation checks missing captions, unsupported audio, duplicate names, sample rate, readable files, and captions that accidentally contain vocal/lyrics terms when the project is marked instrumental.

Default caption behavior uses an instrumental template and filename-derived hints. Caption generation must be reviewable and replaceable; it must never silently overwrite edited captions.

### Training

Provide a named preset `YuE2 Instrumental LoRA` with safe defaults. Expose rank, learning rate, steps, checkpoint interval, regularizer usage, seed, and output folder. The app runs the configured WSL2 command and streams stdout/stderr into the UI.

The default run uses only the selected user dataset. Regularization is opt-in and visibly labeled.

### Checkpoints

List checkpoints by step and training run. Show loss curves, log excerpts, file size, and generated test samples. Support A/B playback and a user-selected preferred checkpoint.

### Export

Convert a selected trainer checkpoint to ComfyUI-compatible `.safetensors`. The user chooses any destination folder. The default is `./exports/`; an optional configured ComfyUI destination can copy the result there. Existing files are never overwritten silently; versioned names are used.

### Settings

Configure WSL distribution, trainer repository, Python executable, model paths, default project directory, optional ComfyUI LoRA directory, and GPU preferences. Validate paths before a run.

## Data flow

```text
audio folder
  -> project dataset import
  -> caption generation + review
  -> validation
  -> WSL2 YuE2 training
  -> checkpoints + samples + logs
  -> checkpoint selection
  -> ComfyUI safetensors conversion
  -> user-selected export folder
```

## Safety and GitHub requirements

- Bind the server to localhost.
- Never delete source audio or captions automatically.
- Keep original checkpoints separate from converted exports.
- Never embed personal Windows paths in source code or committed configs.
- Exclude model weights, private audio, generated samples, logs with local paths, and secrets from Git.
- Ship `.env.example`, path placeholders, setup documentation, and a project template.
- Use versioned output names and explicit overwrite confirmation.

## Initial acceptance criteria

1. A new user can configure paths and open the app on Windows.
2. Importing a folder creates a reviewable captioned dataset.
3. A training run can be started, monitored, stopped, and resumed safely.
4. Checkpoints and samples are visible in the UI.
5. A selected checkpoint converts to a valid ComfyUI LoRA file.
6. Export works to any chosen folder and does not depend on the developer's machine.
