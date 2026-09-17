# YuE Studio

Local Windows UI for preparing music datasets, captioning tracks, training YuE2 instrumental LoRAs, comparing checkpoints, and exporting ComfyUI-compatible safetensors.

## Run the MVP

```powershell
python yue_studio/app.py
```

The app binds to `127.0.0.1` and opens the browser automatically. Configuration is stored in `yue_studio/studio.config.json`, which is ignored by Git.

The current MVP includes project settings, folder scanning, caption sidecars, editable dataset review, and the medieval creator-studio UI. The next integration layer will connect the local ACE-Step captioner, WSL2 trainer, checkpoint converter, and export workflow.
