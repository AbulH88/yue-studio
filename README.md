# YuE Studio

A standalone local Windows app for preparing music datasets, captioning tracks, training YuE2 LoRAs, comparing checkpoints, and exporting ComfyUI-compatible safetensors.

## Run locally

```powershell
python yue_studio/app.py
```

The app binds to localhost only. Model weights, datasets, generated audio, exports, and machine-specific settings are intentionally excluded from Git.

## Connect Ubuntu training

1. Open **Settings** in the left sidebar.
2. Click **Auto Detect**, then **Test Connection**.
3. Add a captioned instrumental dataset to a project.
4. Choose the dataset and training steps, then click **Start Training**.
5. Follow preparation, loss, elapsed time, VRAM, logs, and checkpoints in **Training Runs**.

Every run is created below the configured WSL run workspace with its own manifest, staged source files, preparation data, logs, and creator-format `.pt` checkpoints. The app does not write to the preserved `medieval_echoes_only_raw` run.

The current bridge requires an existing WSL YuE2 environment. Automated installation and ComfyUI conversion are later milestones.

## Training handoff

Before changing the trainer integration, read [docs/TRAINING_HANDOFF.md](docs/TRAINING_HANDOFF.md). It records the verified Mothersuperior-derived Ubuntu training workflow, the successful 14-track run, checkpoint locations, conversion outputs, and the current limits of the UI.
