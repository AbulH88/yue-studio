# ACE-Step Captioning Implementation Plan

1. Verify the ACE-Step GGUF model’s supported local runner and exact command-line interface. Record pinned download sources and model filenames.
2. Add a `CaptionService` that discovers models/runtime, validates tracks, builds safe inference commands, captures output, formats YuE2 captions, and saves only after explicit user action.
3. Extend Setup to report captioner readiness and download missing captioner model assets alongside the local runner.
4. Add caption API routes with dataset-path authorization and tests for format, warnings, path safety, and sidecar overwrite behavior.
5. Add a Caption action on each track plus a dataset-level caption-missing action and review/editor modal.
6. Run unit tests, syntax checks, and a non-destructive runtime/model discovery check. Do not overwrite an existing caption or start a training run.
