# Batch Captioning Plan

1. Extend `CaptionService` with one serialized batch worker, live counters, current track, failures, and completion state.
2. Add batch routes that resolve a saved dataset server-side and return batch status.
3. Add the Tracks-header action, confirmation, progress text, and refresh-on-completion behavior.
4. Test missing-only selection, no-op state, and failure continuation without starting model inference.
5. Run syntax checks and the complete test suite.
