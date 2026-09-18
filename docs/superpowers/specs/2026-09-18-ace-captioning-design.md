# ACE-Step Captioning Design

## Goal

Use the local ACE-Step GGUF captioner to listen to imported audio and produce reviewable, YuE2-ready instrumental captions. Captions are saved as same-stem `.txt` sidecars only after the user reviews or explicitly accepts them.

## Inputs and runtime

The app uses the existing local files:

- `models/captioner/acestep-captioner-Q4_K_M.gguf`
- `models/captioner/acestep-captioner-mmproj-Q8_0.gguf`

Captioning runs through a local llama.cpp-compatible audio-capable executable. Setup detects a compatible executable first and downloads/configures one only if absent. The runtime stays local; audio is never uploaded.

## User flow

Each track row gains a **Caption** action. It opens a review panel with the audio filename, existing caption if any, the generated raw ACE-Step description, and the final YuE2 caption.

Users can choose **Generate caption** for one track or **Caption missing tracks** for a dataset. Existing non-empty captions are never silently replaced. A generated caption remains a draft until **Save caption** is clicked. The action writes the matching `.txt` file beside the source audio and refreshes the track status.

## Formatting and validation

The formatter turns the raw description into a compact tag-style caption. Its fixed ordering is: genre/style, instrumentation, vocal state, tempo/energy, mood, arrangement, production traits. Instrumental projects add `instrumental, no vocals` unless the user changes the project type.

Captions are limited to 1,500 characters and normalized to one comma-separated line. Before saving, validation warns when an instrumental caption contains vocal/lyric/singing language. Warnings do not silently modify user text.

## Service boundaries

- `CaptionService` discovers the model/runtime, queues one caption job at a time, launches the local process, captures logs, formats output, and exposes status.
- App routes validate a track path belongs to a currently scanned dataset, preventing arbitrary file writes.
- The browser UI only calls caption APIs and renders states; it does not handle model processes.

## Failure behavior

If the runtime is missing, the UI gives one Setup action. If model inference fails or its output cannot be parsed, the user receives the raw log and can retry; no `.txt` file is created or overwritten. Captioning may be stopped before the next queued item starts.

## Tests

Unit tests cover model/runtime discovery, command construction, output extraction, YuE2 formatting, instrumental warnings, path authorization, and the rule that existing sidecars require an explicit overwrite choice. Manual validation uses one short audio track and confirms only a user-approved caption writes a `.txt` sidecar.

## Non-goals

- Cloud captioning.
- Automatic overwriting of captions.
- Captioning during a training run.
- Claiming that generated captions are perfect; review remains part of the training workflow.
