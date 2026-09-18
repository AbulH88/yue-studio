# Public installer and launcher design

## Goal

Make a shared YuE Studio project easy for a non-technical Windows user to use.
The project root will be the single obvious entry point. Users will not need a
desktop shortcut or a hidden install directory.

## Public entry points

- `Install YuE Studio.cmd` is the first-run and update entry point. It starts
  the existing PowerShell installer, keeps its console visible for progress and
  errors, and offers to launch YuE Studio when setup completes.
- `Launch YuE Studio.cmd` is the regular entry point. It starts the local
  server and opens the browser.

Both files are double-clickable from a downloaded or cloned project folder.

## Existing scripts

The implementation scripts remain in the root only as internal files with
machine-oriented names:

- `install_yue_studio.ps1` performs installation and updates.
- `launch_yue_studio.cmd` performs the server launch.

The public wrappers call those scripts. Readme/setup documentation will point
only to the two title-cased public entry points. No desktop shortcut is created
or required by this change.

## Safety and failures

The installer retains its existing update detection and never removes user
projects, models, datasets, or training runs. A failed prerequisite or setup
step stays visible in the command window with a useful error instead of opening
a browser that cannot connect. The launcher similarly leaves the command window
open if the app cannot start.

## Verification

Verify that both public wrappers invoke their intended internal scripts, that
documentation points only to public names, and that Python/JavaScript tests and
git whitespace checks pass.
