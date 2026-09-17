# YuE Studio — Direct Training Controls Design

## Goal

Replace the crowded Training Steps preset tiles and redundant fake dropdowns with a compact, direct-input training form. Expose the settings that the isolated WSL trainer actually consumes and record them in each run manifest.

## Training card

The right-side card becomes a focused `Training Configuration` panel:

- Dataset selector.
- Training steps: integer input.
- LoRA rank: integer input.
- Learning rate: numeric scientific-notation input.
- Checkpoint interval: integer input.
- Seed: non-negative integer input.
- One full-width Start Training button.

The `200`, `1000`, and `1500` preset tiles and the separate `Use` button are removed. Users enter the desired value directly.

The existing Base Model and Trainer dropdowns are removed because they currently offer no real choices. A compact read-only summary identifies the active workflow as `YuE2 · Instrumental AR LoRA`.

## Fixed workflow defaults

The panel includes a small visible `Locked trainer defaults` note:

- Artist-only sampling (`artist fraction = 1.0`).
- No regularizer tracks.
- BF16 precision.
- Gradient accumulation: 2.
- Cursor-loss weight: 0.08.
- 50-step warm-up and cosine LR decay with 3,000 schedule steps.

These remain locked in this instrumental-only milestone because they are part of the verified workflow or are not meaningful knobs in the current runner. The app must not imply that a control is adjustable when it is not wired to the trainer.

## Backend and manifest

Start Training accepts and validates direct values:

| Field | Valid range | Default |
| --- | --- | --- |
| Steps | 1–100,000 | 1,000 |
| Rank | 8–256, multiple of 8 | 64 |
| Learning rate | `1e-7`–`1e-3` | `6e-5` |
| Checkpoint interval | 1–steps | 200, capped at steps |
| Seed | 0–2,147,483,647 | 1 |

The validated values are saved in the manifest before staging and passed into the WSL runner. The runner uses the supplied rank, learning rate, checkpoint interval, and seed. Existing default behavior remains unchanged when the user accepts the defaults.

## Error handling and verification

The Start action presents an in-app validation message for invalid values before it calls WSL. Each field keeps its entered value until fixed. Automated tests cover input defaults, rejected ranges, and manifest preservation. Manual checks confirm the compact layout has no step presets or unused dropdowns and that a started run’s manifest matches the displayed inputs.
