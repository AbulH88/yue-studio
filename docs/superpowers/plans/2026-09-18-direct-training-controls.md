# Direct Training Controls Implementation Plan

1. Add one backend validator for steps, rank, learning rate, checkpoint interval, and seed.
2. Store validated input values in each WSL run manifest.
3. Replace the preset-step UI and unused dropdowns with direct inputs and a locked-default summary.
4. Pass all controls from the browser to Start Training and render validation errors in the existing in-app dialog.
5. Add tests for defaults, accepted custom values, and rejected ranges.
6. Run regression checks and restart the local app.
