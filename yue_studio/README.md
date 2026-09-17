# YuE Studio

Local Windows UI for preparing music datasets, captioning tracks, training YuE2 instrumental LoRAs, comparing checkpoints, and exporting ComfyUI-compatible safetensors.

## Run the MVP

```powershell
python yue_studio/app.py
```

The app binds to `127.0.0.1` and opens the browser automatically. Configuration is stored in `yue_studio/studio.config.json`, which is ignored by Git.

The current MVP includes project settings, folder scanning, caption sidecars, editable dataset review, the medieval creator-studio UI, and an instrumental-only WSL2 training bridge.

Open **Settings**, use **Auto Detect**, and run **Test Connection** before starting training. Each run uses an isolated WSL workspace and records its exact inputs and settings in `manifest.json`. Training status and logs appear in **Training Runs**.

Caption-model integration, checkpoint conversion/export, generation, vocal-song training, and the public installer are not implemented yet.
