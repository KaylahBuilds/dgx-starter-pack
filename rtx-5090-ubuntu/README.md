# RTX 5090 Ubuntu Setup

Dedicated workspace for an RTX 5090 machine running Ubuntu.

## Status

Setup has not been implemented or tested. The Ubuntu release, kernel, GPU driver,
and serving runtime still need to be confirmed for the actual host.

## Setup checklist

- [ ] Record the Ubuntu release, kernel, CPU architecture, RAM, and storage.
- [ ] Record the installed RTX 5090 driver and verify GPU detection.
- [ ] Check the chosen runtime's compatibility before changing GPU software.
- [ ] Document local environment creation and model storage.
- [ ] Establish and measure a working single-machine model-serving baseline.
- [ ] Record restart, validation, and recovery steps for the selected setup.
- [ ] Evaluate integration with the DGX Spark only after both baselines work.

## Configuration

Use [config/](config/README.md) for this Ubuntu host's configuration templates.
Keep DGX Spark settings in the separate
[DGX Spark workspace](../dgx-spark/README.md).
