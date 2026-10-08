# DGX Starter Pack

Project workspace for a DGX Spark starter pack, including a future experimental
DGX Spark + RTX 5090 workflow for running a larger model across two machines.

## Status

Initial repository scaffold only. No hardware setup, model serving, distributed
inference, Kubernetes deployment, or benchmarks have been implemented or tested.

## Planned work

- Record the hardware, operating systems, network setup, and software versions.
- Establish and measure a working single-machine model-serving baseline.
- Evaluate the optional two-machine setup against that baseline.
- Add repeatable configuration, setup instructions, and validation checks.
- Introduce k3s and Argo CD deployment examples after the baseline is validated.

Model weights, private datasets, credentials, and local experiment output do not
belong in Git. Add example configuration with placeholders, not real secrets.

The OneWorld GTA mod release is a separate project and is not included here.
