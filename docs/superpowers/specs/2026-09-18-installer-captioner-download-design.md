# Installer captioner download design

## Goal

Make `Install YuE Studio.cmd` install a working local ACE-Step captioner without
requiring a user to understand Setup, model folders, or command-line tools.

## Installer flow

The visible installer command window will:

1. Copy or update the application under `%LOCALAPPDATA%\YuE Studio`.
2. Download the two pinned ACE-Step captioner model files into
   `models\captioner` below that installed app.
3. Verify each file against its pinned SHA-256 checksum.
4. Install the compatible local captioner engine into
   `models\captioner\engine` using the existing engine installer.
5. Verify that `llama-server.exe` exists, then launch Studio.

The model source is revision `732354f20c9dd5fa1c037d0e301e8bf837c1cf8e` of
`dernet/acestep-captioner-GGUF`. The expected SHA-256 values are
`1c6fb97c2599dc259af70bbfc89a65da24360ba55d7b982366ca32f7e2ae8786` for
`acestep-captioner-Q4_K_M.gguf`, and
`77f15ee6e123a85deb2e853ef08d791613e2350c3cd24e033e99e6bad027a8b8` for
`acestep-captioner-mmproj-Q8_0.gguf`.

## Visibility and retries

The `.cmd` window stays open throughout. Each install stage is printed, and
the downloader shows normal transfer progress. Existing verified files are
reported and skipped. A missing, corrupt, or failed download stops installation
with an error visible in that same window; the app is not launched as ready.

## Scope

This installs the captioner only. The larger YuE2 training models and WSL
training environment remain in the app's full Setup flow, because they have
their own Ubuntu/GPU requirements.

## Verification

Verify script syntax and static references, confirm installer output calls the
captioner download and engine steps before launch, then run the Python tests and
git whitespace check.
