# Guided WSL Setup Design

## Goal

Let a non-technical Windows user prepare YuE Studio for YuE2 LoRA training without entering Linux paths, creating a Python environment, or manually installing packages. The existing verified WSL/Ubuntu training workflow remains the only training engine.

## Scope

The app gains a guided setup screen and a backend setup service. It detects what is already available and guides the user through the minimum required actions:

1. Check WSL, an Ubuntu distribution, NVIDIA/CUDA availability, and disk space.
2. If WSL or Ubuntu is absent, present the exact one-click Windows command and state that Windows may request administrator approval and a restart. The app must not claim it can bypass either requirement.
3. Create an app-owned Ubuntu virtual environment and install the verified Python dependencies and FFmpeg.
4. Download required YuE2 model assets into standard app-managed Ubuntu folders, with item-level progress, size, failure reason, retry support, and a disk-space estimate.
5. Verify the complete environment, save the discovered settings, and unlock training.

## User experience

At first launch, users see a setup state instead of raw training paths. The primary action is **Set Up YuE Studio**. A checklist reports simple states: Ready, Installing, Needs your approval, Needs restart, or Problem. Detailed command output lives behind **Show details**.

The wizard resumes from its last completed step. Existing expert installations are detected and adopted through the current Auto Detect and preflight checks; nothing is removed or overwritten. Settings remains an Advanced area for repair and custom paths.

Model downloads use a versioned manifest owned by YuE Studio. Public files download directly. A gated Hugging Face file pauses at a clear **Sign in to Hugging Face** step and continues only after authentication succeeds. No credentials are stored in the project config or committed to Git.

## Architecture

- `SetupService` owns capability detection, persisted setup status, package installation, model manifest resolution, downloads, and verification.
- The existing `TrainingBridge` remains responsible for training and provides the final preflight contract. Setup succeeds only if its preflight passes.
- Setup commands run in the selected WSL Ubuntu distribution. The setup-created environment and models live in app-managed Linux directories, separate from the preserved historical run and user datasets.
- The HTTP API exposes setup status, start, logs/progress, retry, and model-auth state. The frontend polls status and never invokes browser-native prompts.

## Safety and recovery

- Never modify historical `medieval_echoes_only_raw`, existing model folders, user datasets, or existing runs.
- Download to a temporary file and atomically promote only after the transfer/checksum succeeds.
- Check available disk space before each model download and explain insufficient space plainly.
- Serialize setup work so only one setup process can run. It is safe to close and reopen the app; the next launch rechecks and resumes incomplete work.
- Failed commands preserve their logs and expose a retry action. The user can open Advanced settings to repair paths without deleting anything.

## Testing

- Unit-test state transitions, manifest validation, command construction, error mapping, and preservation of existing settings.
- Test WSL absent, restart-needed, Ubuntu absent, no GPU, insufficient disk, package failure, download interruption, gated model authentication, and an already configured machine.
- Run the final preflight against this computer's verified Ubuntu environment. Do not start a training run as part of setup validation.

## Non-goals

- Docker support.
- A public installer/packager; this is the in-app setup foundation for one later.
- ComfyUI checkpoint conversion, caption generation, generation/testing, or low-VRAM block swapping.
