# Launcher and Automatic Updates Design

## Goal

Make YuE Studio feel like a normal Windows app: installation ends by launching the app, later launches use a desktop shortcut, and updates happen automatically without risking user work or an active training run.

## Launcher and installer behavior

The project will include a Windows installer script that creates a desktop shortcut named **YuE Studio**. Double-clicking it starts the local server if it is not already running and opens the browser at the local app page.

When installation completes successfully, the installer launches that shortcut immediately. It does not require the user to find a folder, open PowerShell, or copy a localhost address. The shortcut reports a simple error if Python is unavailable or the server cannot start.

## Update behavior

At launch, the app checks a signed/versioned release manifest over HTTPS. If an update is available and no training or setup worker is active, it downloads it in the background. App code, Python packages, small training assets, and large model assets are all included.

Large model downloads report progress in Setup. Existing working model folders remain untouched while an update downloads to a versioned temporary folder. Only after checksum validation and final preflight succeeds does the app switch the active paths. A failed update keeps the previous version active. Updates never touch projects, datasets, source music, training runs, or checkpoints.

## Safety boundaries

- No update begins while a training run or environment setup is active.
- WSL/Ubuntu installation still requires Windows approval/restart where Windows requires it.
- Model releases are pinned by manifest revision and SHA-256, not an unreviewed moving `main` branch.
- The first GitHub release provides the manifest and packaged installer. Before that, the app reports that automatic updates are not yet published instead of failing.

## Deliverables

- A version file and release manifest reader.
- A safe updater with staging, checksum verification, preflight, activation, rollback, and progress reporting.
- A Windows launcher script, desktop shortcut creation, and installer that launches the app on completion.
- Tests for update eligibility, manifest validation, staging/activation rollback, and launcher command construction.

## Non-goals

- Silent Windows elevation or bypassing a required restart.
- Updating during a training run.
- Publishing a GitHub release in this change; the updater is prepared for the first release.
