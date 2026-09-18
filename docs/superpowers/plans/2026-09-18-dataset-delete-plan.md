# Dataset Delete Plan

1. Add a dataset delete route that removes exactly one named saved dataset and preserves all other local configuration.
2. Add backend tests for successful deletion, unknown dataset handling, and final-dataset empty state.
3. Add an in-app Delete action on dataset cards using the existing confirmation modal.
4. Refresh dataset selection, tracks, and training controls after successful deletion.
5. Run Python/JavaScript checks and the full test suite.
