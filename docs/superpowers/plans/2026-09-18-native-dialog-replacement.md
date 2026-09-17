# Native Dialog Replacement Implementation Plan

1. Add source-aware dataset scanning and Windows-native folder/file picker endpoints to the local backend.
2. Preserve legacy folder datasets while storing new datasets as explicit file/folder sources.
3. Replace all browser-native prompts, alerts, and confirmations with a reusable in-app modal, confirmation modal, and toast notifications.
4. Build the project and dataset forms, including file/folder selection, source list, preview, removal, inline validation, and busy states.
5. Update training to receive the selected dataset's exact source list.
6. Add backend tests for source scanning and run JavaScript/Python checks, then restart the local server.
