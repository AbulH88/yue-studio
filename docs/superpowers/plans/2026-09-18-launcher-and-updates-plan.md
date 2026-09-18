# Launcher and Automatic Updates Plan

1. Add app version and release-manifest support. Validate HTTPS manifests, compare versions, and expose update status without treating an unpublished release as an error.
2. Add update eligibility and state handling. Do not update during setup or training; stage a release, validate hashes, preserve the active release, and provide rollback metadata.
3. Add a Windows `launch_yue_studio.cmd` that starts the local server and opens the browser. It reuses a running server when present.
4. Add a PowerShell installer that copies the application to a user-local install directory, creates a desktop shortcut, launches it at the end, and never requires a terminal afterward.
5. Add a Setup UI update-status row and background launch-time check.
6. Add unit tests for version comparison, manifest validation, update eligibility, and launch command construction. Run compilation, tests, and a launcher smoke test without overwriting the current checkout.
