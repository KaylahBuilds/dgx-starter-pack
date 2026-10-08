# DGX Starter Pack

Dedicated workspace for a DGX Spark setup and an RTX 5090 host running Ubuntu,
including a future experimental workflow for running a larger model across the
two machines.

## Status

The repository now includes an [Argo CD / k3s GitOps example for DGX Spark](dgx-spark/gitops/README.md),
matching the [companion blog](https://kaylahbuilds.io/#/blog/dgx-spark-gitops-k3s-argocd).
It includes staged app-of-apps manifests, GPU checks, model/gateway templates,
optional monitoring/networking, and offline validation. No hardware installation,
cluster deployment, GPU execution, inference, distributed serving, or benchmark
has been performed. The RTX 5090 workspace remains a planning scaffold.

## Machine workspaces

- [DGX Spark setup](dgx-spark/README.md) — setup checklist and machine-specific configuration.
- [RTX 5090 on Ubuntu](rtx-5090-ubuntu/README.md) — Ubuntu setup checklist and machine-specific configuration.

Each workspace has its own `config/` folder. The Spark also has a `gitops/`
example with deliberately opt-in workloads. Machine configuration outside that
example remains a planning scaffold, not a tested model-serving stack.

## Planned work

- Record the hardware, operating systems, network setup, and software versions.
- Establish and measure a working single-machine model-serving baseline.
- Evaluate the optional two-machine setup against that baseline.
- Add repeatable configuration, setup instructions, and validation checks.
- Validate the GitOps example on actual Spark hardware after the baseline works.

Model weights, private datasets, credentials, and local experiment output do not
belong in Git. Add example configuration with placeholders, not real secrets.
