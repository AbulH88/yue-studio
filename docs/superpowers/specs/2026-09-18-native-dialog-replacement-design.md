# YuE Studio — Native Dialog Replacement Design

## Goal

Remove every browser-native `prompt`, `alert`, and `confirm` interaction from YuE Studio. Replace them with accessible, branded in-app dialogs, inline validation, and non-blocking notices that match the existing medieval studio interface.

The dataset workflow must let a user link one audio file, multiple audio files, or a whole folder from the Windows computer without copying or uploading the source audio.

## Shared interaction system

Add one reusable modal layer with a darkened backdrop, parchment-and-green visual treatment, clear title and description, keyboard focus, Escape-to-close behavior, and explicit Cancel/primary actions. Destructive confirmation uses the same component with a red treatment.

Add a small toast area for success and informational messages. Validation and API failures appear inside the relevant dialog instead of in browser alerts.

The modal layer covers:

- Create project.
- Delete project confirmation.
- Add dataset.
- Training-step validation feedback.
- Training start errors.
- Stop-training confirmation and errors.

No `prompt()`, `alert()`, or `confirm()` calls remain in application JavaScript.

## Create Project dialog

The Create New Project button opens a branded dialog containing a project-name field. The primary action stays disabled until the trimmed name is non-empty. Enter submits, Escape cancels, and focus begins in the name field.

This milestone preserves the current in-memory project behavior; persistent multi-project storage remains separate work.

## Add Dataset dialog

The dialog contains:

- Editable dataset name.
- **Add Files** button for one or multiple supported audio files.
- **Add Folder** button for a linked folder whose supported audio files are scanned recursively.
- A selected-source summary and removable source rows.
- A preview showing detected track count and supported formats.
- Inline errors for missing name, empty selection, missing paths, unsupported files, duplicates, or a folder with no supported audio.
- Cancel and Add Dataset actions.

The Windows selections are made by the local Python backend with native file/folder pickers. The browser receives selected absolute paths only after the user confirms the operating-system picker. Cancelling a picker changes nothing.

Source audio is referenced in place. It is not moved, copied, uploaded, renamed, or modified.

## Dataset data model

Each dataset stores a `sources` list. A source is either:

```json
{"type": "file", "path": "C:\\Music\\track.flac"}
```

or:

```json
{"type": "folder", "path": "C:\\Music\\Album"}
```

Existing datasets containing only a legacy `path` field continue to work and are treated as one folder source.

Scanning combines all sources, recursively scans folders, accepts MP3, WAV, FLAC, OGG, and M4A, removes duplicate resolved file paths, and returns a stable sorted track list. A selected file uses its adjacent same-stem `.txt` caption sidecar. Training receives this exact scanned track list, so mixed file/folder datasets work without staging unrelated files.

## Local picker API

Add localhost-only endpoints for:

- Selecting one or more supported audio files.
- Selecting one folder.
- Previewing a proposed source list before saving.

The backend opens a native Windows picker on the same desktop that launched YuE Studio. Only picker results are returned; arbitrary commands are never accepted. The existing localhost binding remains unchanged.

Dataset creation accepts a name and structured sources. The server validates every source again rather than trusting the browser preview.

## Error handling

- Only one in-app modal is open at once.
- Picker cancellation is silent and preserves previous selections.
- Backend errors remain visible in the dialog until corrected.
- Duplicate files selected directly and through a folder appear once.
- Missing sources are identified by path.
- The Add Dataset button shows a busy state while previewing or saving.
- Success closes the dialog, refreshes the dataset list, selects the new dataset, and displays a toast with the number of tracks found.

## Verification

Automated tests cover legacy folder datasets, explicit file sources, recursive folder sources, mixed-source deduplication, unsupported files, missing sources, and picker-result validation. JavaScript checks verify that native browser dialog calls are absent.

Manual verification covers keyboard behavior, picker cancellation, single-file selection, multi-file selection, whole-folder selection, removing a selected source, inline error display, dataset creation, project creation, deletion confirmation, training errors, and stop confirmation.

## Acceptance criteria

1. No browser-native prompt, alert, or confirmation dialog appears anywhere in YuE Studio.
2. All dialogs visually match the application and remain usable by keyboard.
3. A dataset can reference one file, multiple files, one folder, or a mixture of files and folders.
4. Selected audio remains in its original location and is never copied or changed.
5. Existing folder-based datasets remain readable.
6. The displayed dataset track list and the training input track list are identical.
