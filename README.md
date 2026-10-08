# DGX Starter Pack

Dedicated workspace for a DGX Spark setup and an RTX 5090 host running Ubuntu,
including a future experimental workflow for running a larger model across the
two machines.

## Status

Initial repository scaffold only. No hardware setup, model serving, distributed
inference, Kubernetes deployment, or benchmarks have been implemented or tested.

## Machine workspaces

- [DGX Spark setup](dgx-spark/README.md) — setup checklist and machine-specific configuration.
- [RTX 5090 on Ubuntu](rtx-5090-ubuntu/README.md) — Ubuntu setup checklist and machine-specific configuration.

Each workspace has its own `config/` folder. Configuration is currently a
planning scaffold, not an installation script or a working model-serving stack.

## Planned work

- Record the hardware, operating systems, network setup, and software versions.
- Establish and measure a working single-machine model-serving baseline.
- Evaluate the optional two-machine setup against that baseline.
- Add repeatable configuration, setup instructions, and validation checks.
- Introduce k3s and Argo CD deployment examples after the baseline is validated.

Model weights, private datasets, credentials, and local experiment output do not
belong in Git. Add example configuration with placeholders, not real secrets.
