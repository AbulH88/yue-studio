# Project-local installation design

## Goal

YuE Studio must remain completely inside the folder that a person downloads,
clones, or shares. It must not copy the application or captioner assets into
`AppData`.

## Installation location

`Install YuE Studio.cmd` invokes its PowerShell installer with the project root
as the installation root. The installer does not copy application files. It
creates and reuses only project-local runtime folders such as `models`,
`projects`, `exports`, `.updates`, and machine-local configuration.

The captioner model files live at `models\captioner`, and its engine lives at
`models\captioner\engine`, both below the project root. The launcher starts
`yue_studio\app.py` from that same root, so the running app always sees those
files.

## Reinstall and update behavior

Running the installer again verifies existing captioner model files and reuses
them rather than downloading them again. It refreshes the local captioner engine
only when its required executable is absent. Project-local pending updates still
apply through the existing launcher behavior.

## Existing accidental installation

No automated deletion will be performed on the prior `%LOCALAPPDATA%\YuE
Studio` folder. It may contain downloaded files, and removing it needs explicit
user direction. New installation and launch behavior will ignore it.

## Verification

Verify that neither public command includes an `AppData` install path, that
models and engine target the project root, and that test and syntax checks pass.
