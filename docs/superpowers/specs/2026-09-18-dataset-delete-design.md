# Dataset Delete Design

## Goal

Allow a user to remove a dataset from a YuE Studio project without deleting linked source audio, caption sidecars, models, checkpoints, run folders, or exports.

## Interaction

Each dataset card displays a small **Delete** action. Selecting it opens the existing in-app confirmation dialog, naming the dataset and stating plainly that only its YuE Studio link will be removed.

On confirmation the dataset entry is removed from local configuration, the selected dataset falls back to the next available dataset, and the dataset picker, track table, and training controls refresh. If no datasets remain, the normal empty state returns.

## API and safety

The delete endpoint accepts a dataset name, matches only a saved dataset entry, and returns an error for an unknown name. It changes only the ignored local configuration file. It never follows dataset source paths or runs filesystem deletion commands.

## Tests

Test deletion of one dataset among several, dataset-not-found error behavior, config preservation for unrelated fields, and the empty-state result after deleting the final dataset.
