# Batch Captioning Design

## Goal

Caption every missing track in a selected dataset with the local ACE-Step captioner through one explicit user action.

## Interaction

The Tracks header gains **Caption All Missing**. It states the number of eligible tracks and asks for confirmation. When accepted, the screen shows current track name, completed count, and failures while the batch runs.

## Behavior and safety

Tracks are processed serially through the same ACE-Step service used for individual captioning. Each successful generated YuE2 caption is written to its matching `.txt` sidecar. Existing non-empty captions are skipped and never overwritten. A failure is recorded for that track and processing continues with later tracks. A final summary reports saved, skipped, and failed counts.

The action is unavailable while a batch is active, ACE-Step is not ready, or training is active. It uses only tracks currently linked to the selected dataset; arbitrary paths are rejected.

## API and tests

The backend owns a single serialized batch worker and status object. Routes start a batch and return progress/status. Tests cover missing-only selection, all-captioned no-op, individual failure continuation, duplicate start rejection, and config/source isolation.
