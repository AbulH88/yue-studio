# YuE Studio

A standalone local Windows app for preparing music datasets, captioning tracks, training YuE2 LoRAs, comparing checkpoints, and exporting ComfyUI-compatible safetensors.

## Run YuE Studio

```powershell
python yue_studio/app.py
```

The app opens locally at `http://127.0.0.1:8765`. Model weights, datasets, generated audio, exports, and machine-specific settings are intentionally excluded from Git.

## First-time setup

Open **Setup** in the left sidebar and press **Set Up YuE Studio**. It prepares the Ubuntu Python environment, FFmpeg, required Python packages, and YuE2 training assets for you. It then verifies the GPU, models, and workspace before it reports Ready.

The first setup downloads roughly 11 GB of model files and needs about 18 GB free disk space. If Ubuntu/WSL is not present, the app shows the one Windows command required to install it. Windows may ask for administrator approval and a restart; return to Setup afterward and press **Continue Setup**.

If an existing YuE2 environment is already working, the app detects it and leaves it untouched. **Advanced** is only for repairs or custom locations.

## Install and launch with a double-click

For a normal Windows install, download the YuE Studio release ZIP, extract it,
and double-click **`Install YuE Studio.cmd`**. It installs or safely updates the
app and opens it automatically when it finishes.

After that, double-click **`Launch YuE Studio.cmd`** in the project folder
whenever you want to open the app. No desktop shortcut or terminal commands are
needed.

The app checks for published updates on launch. Updates download safely in the background and install automatically on the next launch, never while setup or training is running.

## Train an instrumental LoRA

1. Add a captioned instrumental dataset to a project.
2. Choose the dataset and training values.
3. Click **Start Training**.
4. Follow preparation, loss, elapsed time, VRAM, logs, and checkpoints in **Training Runs**.

Every run is created below the configured WSL run workspace with its own manifest, staged source files, preparation data, logs, and creator-format `.pt` checkpoints. The app does not write to the preserved `medieval_echoes_only_raw` run.

The setup process uses the verified WSL/Ubuntu workflow. It does not use Docker.

## Training handoff

Before changing the trainer integration, read [docs/TRAINING_HANDOFF.md](docs/TRAINING_HANDOFF.md). It records the verified Mothersuperior-derived Ubuntu training workflow, the successful 14-track run, checkpoint locations, conversion outputs, and the current limits of the UI.
