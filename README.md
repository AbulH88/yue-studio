# YuE Studio

A standalone local Windows app for preparing music datasets, captioning tracks, training YuE2 LoRAs, comparing checkpoints, and exporting ComfyUI-compatible safetensors.

## Run locally

```powershell
python yue_studio/app.py
```

The app binds to localhost only. Model weights, datasets, generated audio, exports, and machine-specific settings are intentionally excluded from Git.

## Training handoff

Before changing the trainer integration, read [docs/TRAINING_HANDOFF.md](docs/TRAINING_HANDOFF.md). It records the verified Mothersuperior-derived Ubuntu training workflow, the successful 14-track run, checkpoint locations, conversion outputs, and the current limits of the UI.
