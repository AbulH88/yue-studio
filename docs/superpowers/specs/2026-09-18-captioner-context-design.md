# Captioner context capacity design

## Problem

The local ACE-Step server currently starts with a 4,096-token context. A tested
three-minute track produces 4,864 audio tokens and is rejected before caption
generation with HTTP 400.

## Decision

Start the local captioner with an 8,192-token context. This supports ordinary
three-to-four-minute songs without silently trimming their audio. It uses more
GPU memory than the prior setting, but is appropriate for the target RTX 5090
system.

## Behavior

The setting applies when YuE Studio next starts its local captioner process. It
does not change a dataset, a saved caption, the YuE2 training configuration, or
the installed model files. If the engine reports another request error, the UI
will continue to display it rather than pretending a caption was made.

## Verification

Check that the server launch command uses 8,192, run syntax and automated
tests, and manually retry the previously failing track after restarting Studio.
