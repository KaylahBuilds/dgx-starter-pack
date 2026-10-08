# DGX Spark Setup

Dedicated workspace for setting up, documenting, and validating the DGX Spark.

## Status

Setup has not been implemented or tested. Record the actual machine details
before adding installation steps or choosing driver and runtime versions.

## Setup checklist

- [ ] Record hardware, memory, storage, operating system, and CPU architecture.
- [ ] Record the installed GPU driver and available software versions.
- [ ] Document the network connection and available disk space.
- [ ] Select a model-serving runtime compatible with this machine.
- [ ] Establish a working single-machine baseline before testing a second host.
- [ ] Record reproducible commands and benchmark results without private data.

## Configuration

Use [config/](config/README.md) for this machine's configuration templates.
Keep Ubuntu RTX 5090 settings in the separate
[RTX 5090 workspace](../rtx-5090-ubuntu/README.md).
