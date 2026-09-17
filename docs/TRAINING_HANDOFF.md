# YuE Studio: YuE2 Instrumental LoRA Training Handoff

Last verified: 2026-09-18

## Definitive result

The successful `medieval_echoes` instrumental LoRA was **not** trained with AI Toolkit.
It was trained inside Ubuntu/WSL2 with a Mothersuperior-derived YuE2 AR LoRA workflow,
then converted from creator-format `.pt` checkpoints to ComfyUI-compatible
`.safetensors` files.

The successful test used only the user's 14 medieval instrumental tracks. The
1,000-step conversion was tested in ComfyUI and produced instrumental output without
the unwanted singing heard from the 200-step conversion.

## Important history

Several earlier AI Toolkit experiments took place, including an official checkout and
a temporary `ai-toolkit-yue2-optimized` checkout. Those runs were stopped, failed, or
were discarded. They are not the source of the working 200/1,000-step AR LoRAs.

Do not use this surviving file as the recipe for the successful AR run:

```text
G:\Doc Aitool\ai-toolkit-official\output\medieval_echoes\config.yaml
```

That file belongs to an earlier official AI Toolkit diffusion-training attempt which
was stopped at step 8 because of excessive memory use.

## Trainer and installed components

Windows-side copy of the Mothersuperior-derived scripts:

```text
G:\Doc Aitool\yue2-mothersuperior-trainer
```

Training script used by the preserved run:

```text
G:\Doc Aitool\yue2-mothersuperior-trainer\scripts\ar_lora_cursor.py
```

Ubuntu/WSL2 contains:

```text
/home/jimi/yue2-venv       YuE2 Python environment
/home/jimi/yue2-raw        local raw YuE2 model used by the trainer
/home/jimi/mert-fullsong   MERT-v2-FullSong files
/home/jimi/yue2-base-vae   YuE2 VAE files
/home/jimi/yue2-work       tokenizer/regularizer preparation assets
/workspace                 training data, prepared datasets, and outputs
```

The GPU was an RTX 5090. The successful run used approximately 13.5 GB VRAM.

## What came from the author's guide

The setup followed Mothersuperior's published AR instrumental LoRA recipe rather than
inventing a new architecture. The published recipe values used as the starting point
were:

- AR-branch LoRA targeting all 28 YuE2 transformer layers.
- Targets: `self_attn.{q,k,v,o}_proj` and
  `mlp.{gate,up,down}_proj`.
- Rank 64.
- Learning rate `6e-5`.
- Two-step gradient accumulation.
- Cursor-loss weight `0.08`.
- Checkpointed training with early checkpoints retained.
- The author's full recipe mixes artist/real data and regularizer data 50/50.

The author's Hugging Face model card is:

```text
https://huggingface.co/Mothersuperior/YuE2-instrumental-cot-full-loras
```

## Our successful variation

The first intended recipe was the author's 50/50 regularizer mix. The corrected run
changed the artist fraction to `1.0`, so it sampled only the user's 14 tracks and used
no regularizer songs.

Confirmed run settings:

| Setting | Value |
| --- | --- |
| Run name | `medieval_echoes_only_raw` |
| Dataset | User's 14 medieval instrumental tracks only |
| Steps | 1,000 |
| Rank | 64 |
| Learning rate | `6e-5` |
| Artist fraction | `1.0` |
| Regularizer songs | None in the corrected run |
| Gradient accumulation | 2 |
| Cursor-loss weight | `0.08` |
| Optimizer | AdamW, betas `(0.9, 0.95)`, zero weight decay |
| Gradient clipping | `1.0` |
| Model precision | BF16 |
| Training format | AR, score-free `cot=off` token prefix |
| LoRA targets | AR attention q/k/v/o plus MLP gate/up/down |
| LoRA tensors | 392 |
| Maximum sequence length | 12,288 tokens |
| LR schedule | 50-step warm-up followed by cosine decay |
| Checkpoint interval | Every 200 steps in this run |
| Approximate VRAM | 13.5 GB |

The launch command is not retained verbatim in a shell history. Based on the preserved
script's positional arguments and the settings recorded during the run, it was
equivalent to:

```bash
python ar_lora_cursor.py medieval_echoes_only_raw 1000 64 1.0 none 6e-5 0.08
```

Do not present this reconstructed line as a byte-for-byte recovered command. The
settings themselves are supported by the screenshots, script, checkpoints, and log.

## Preserved original checkpoints

The creator-format checkpoints are still present inside WSL2:

```text
\\wsl$\Ubuntu\workspace\tok\full\medieval_echoes_only_raw\
```

Files verified there:

```text
best.pt
last.pt
step-200.pt
step-400.pt
step-600.pt
step-800.pt
step-1000.pt
train.log
```

Each inspected step checkpoint reports:

```text
rank: 64
targets: ar self_attn qkvo + mlp gate/up/down
lora tensors: 392
```

## Training behavior

The preserved log is:

```text
\\wsl$\Ubuntu\workspace\tok\full\medieval_echoes_only_raw\train.log
```

Key evaluation values:

| Step | Artist loss | Held-out/minted validation loss |
| ---: | ---: | ---: |
| 0 | 4.466 | 3.608 |
| 100 | 3.258 | 3.761 |
| 200 | 2.237 | 3.896 |
| 400 | 0.612 | 4.329 |
| 600 | 0.092 | 4.883 |
| 800 | 0.045 | 5.250 |
| 1,000 | 0.026 | 5.420 |

The falling artist loss and rising validation loss show heavy overfitting. The original
recommendation was therefore to test step 200 first. Listening tests ultimately found:

- Step 200 still generated unwanted voice/vocal behavior.
- Step 1,000 produced the desired instrumental result.

Listening quality is the deciding evidence here; loss alone did not predict which
checkpoint satisfied the user's instrumental goal.

## ComfyUI conversions

The converted files are currently located at:

```text
G:\ConfiuiModels\models\loras\YuE2\medieval_echoes_step200_comfyui.safetensors
G:\ConfiuiModels\models\loras\YuE2\medieval_echoes_step1000_comfyui.safetensors
```

These are conversions of the WSL creator-format AR `.pt` checkpoints. They are not AI
Toolkit outputs. The 1,000-step file is the successful tested version.

Because this is an AR LoRA, its ComfyUI placement/connection must target YuE2's AR/CLIP
side using the same native key conversion used previously. Do not treat it as a NAR
MODEL-only LoRA.

## YuE Studio status

Repository:

```text
G:\YuE Studio
```

Currently working:

- Local Windows web app served on `127.0.0.1:8765`.
- Project library and project navigation.
- Local dataset creation by name and Windows folder path.
- Scanning MP3, WAV, FLAC, OGG, and M4A files.
- Track list, duration probing, and `.txt` caption-sidecar detection.
- Editable training-step field in the UI.

Not implemented yet:

- The Start Training button does not launch WSL training.
- Training progress/log streaming is not connected.
- Checkpoint discovery and conversion are not connected.
- Caption generation is not connected to a real local captioning model.
- Generate/Test is not connected to YuE2/ComfyUI.
- Project state is still minimal and not a complete persistent multi-project database.

The next agent must not describe YuE Studio as a finished trainer until these pieces are
actually wired and tested.

## Recommended next implementation

1. Preserve the existing successful checkpoints and trainer scripts without altering
   them.
2. Add a small WSL runner interface to YuE Studio that validates Ubuntu, CUDA, the
   environment, model paths, dataset preparation, and free disk space.
3. Save every run to a project-specific manifest before launching. Include all command
   arguments, script hash/commit, dataset file list, model path/revision, timestamps,
   and output directory.
4. Launch the preserved Mothersuperior-derived AR trainer through WSL using the selected
   dataset and explicit settings.
5. Stream stdout/stderr and parse step, loss, evaluation, elapsed time, and VRAM into
   the Training Runs screen.
6. Discover `.pt` checkpoints from the run directory and display them without assuming
   `best.pt` is perceptually best.
7. Convert a selected checkpoint to ComfyUI format, preserving conversion metadata.
8. Export to a user-selected directory; do not silently write into an external ComfyUI
   installation.
9. Add a reproducible listening test that records prompt, mode, seed, LoRA strength,
   checkpoint, and generated audio.

## Safety and reproducibility rules

- Do not delete or overwrite the WSL checkpoint directory.
- Do not silently fall back to AI Toolkit.
- Do not mix NAR and AR LoRA loading instructions.
- Do not claim the author's 50/50 regularizer recipe was used by the successful run;
  the successful corrected run used `artist_frac=1.0`.
- Keep creator-format `.pt` files and converted ComfyUI `.safetensors` files separate.
- Save the exact command and configuration manifest before any future training starts.
- Treat generated audio listening tests as separate evidence from training loss.

