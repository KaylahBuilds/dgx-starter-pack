# DGX Spark GitOps example

The companion example for [Build a GitOps Platform on DGX Spark Before Your First
Model](https://kaylahbuilds.io/#/blog/dgx-spark-gitops-k3s-argocd).

This is a single-node, trusted-lab example, not a production installation or a
claim of hardware validation. The manifests can be rendered and checked offline;
no Spark, GPU, model, or cluster was accessed while creating them. Kubernetes is
optional for a quick model experiment. Establish a compatible single-machine
baseline before using this platform for persistent services.

## What you get

- An Argo CD Helm **app-of-apps** with separate child Applications.
- A GPU Operator profile preserving Spark's existing driver/toolkit, with legacy
  `nvidia` runtime selection and DCGM exporter disabled.
- Two durable GPU Jobs: device visibility, then verified CUDA arithmetic.
- A digest/revision-gated model Deployment with one GPU, one replica, `Recreate`,
  persistent cache, startup/readiness probes, and a private Service.
- An optional LiteLLM alias gateway using an external authentication Secret.
- Optional Prometheus monitoring and NVIDIA Network Operator registration.
- Bootstrap, validation, Git-change, shutdown, and recovery exercises.
- Offline Helm/YAML safety checks, including deliberate negative controls.

## Stages and defaults

| Child Application | Included initially? | Workload sync | Purpose |
| --- | --- | --- | --- |
| `dgx-workload-defaults` | Yes | Automatic; self-heal; no pruning | Service account and resource defaults |
| `dgx-gpu-operator` | Yes | **Manual** | Device plugin/discovery; host stack preserved |
| `dgx-gpu-validation` | No | Manual | Run only before model allocation |
| `dgx-model-service` | No | Automatic; self-heal; no pruning | Enable only after real model validation |
| `dgx-model-gateway` | No | Manual | Private authenticated alias routing |
| `dgx-monitoring` | No | Manual | Host/Pod/storage and serving metrics |
| `dgx-accelerated-networking` | No | Manual | Optional hardware-specific networking |

The root automatically registers the enabled children. It does **not** imply
GPU readiness or automatically deploy manual children. Sync waves on validation
Jobs order visibility before compute, but are not a general dependency engine
between child Applications. Check each gate explicitly.

```text
bootstrap/root-application.yaml
  -> platform/ Helm chart (admin-owned Git)
     -> workload defaults
     -> GPU Operator (manual)
     -> GPU checks -> model service -> gateway (opt-in)
     -> monitoring / accelerated networking (opt-in)
```

## Start here

1. [Check versions and compatibility](docs/versions.md).
2. [Bootstrap the lab](docs/bootstrap.md).
3. [Validate the GPU and enable a model](docs/validation.md).
4. [Enable optional services](docs/optional-services.md).
5. [Practice changes, shutdown, and recovery](docs/operations.md).

All paths in the commands are relative to the repository root. Before using a
fork, replace the repository URL in both bootstrap manifests and
`platform/values.yaml`. Review every `project` and `destination` change.

## Offline checks (no cluster or API credentials)

With Python 3.12+ and Helm 3.19.0 installed:

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r dgx-spark/gitops/requirements-validation.txt
python dgx-spark/gitops/tools/validate.py --helm helm
```

The validator renders the actual charts with synthetic, non-deployable image and
model identifiers in an isolated ignored cache directory. It checks defaults,
gates, projects, GPU allocation, private Services, durable Jobs, and external
Secret references. Synthetic fixtures are **not** compatible images or tested
models. Do not deploy validator output.

The validation command runs all 24 checks. Static checks are not Kubernetes admission checks, CUDA execution, inference
tests, security certification, or performance benchmarks. Use the validation
guide on actual hardware to obtain those results.

## Trust and credentials

App-of-apps is an **admin-only** pattern. The root can create Applications in
other projects; `dgx-infrastructure` necessarily permits cluster-level operator
resources. Project separation is useful guardrailing, not multi-tenant isolation.
Limit write access, review changes, and protect the deployment branch.

Never commit credentials, kubeconfigs, API keys, registry logins, generated
Secrets, model weights, or private datasets. The public repo requires no Git
credential to read. Secrets are created outside Git or supplied by an external
secret manager. A base64-encoded Secret is still a credential.

Services have no public ingress or LoadBalancer. NetworkPolicies narrow normal
Pod ingress if the CNI enforces them; cluster administrators, host processes,
and authorized port-forward access remain trusted. The raw model endpoint has
no API authentication in this lab contract. Do not expose it publicly.

Spark has unified CPU/GPU memory, not a separate 128 GB VRAM budget. Resource
defaults are illustrative: measure host, serving-engine, and storage use before
raising limits. A PVC is not a backup; one node is a single point of failure.
