# Bootstrap a trusted Spark lab

These are **operator-run instructions**, not actions performed by this project.
Use a non-production single Spark. Review the commands, host state, compatibility,
backup plan, and available disk space first. Do not apply the Spark profile to the
RTX 5090 host or join it to the cluster as part of this example.

## 1. Record the existing host stack

On the Spark, outside any automated installation:

```sh
uname -m                         # Expected aarch64
cat /etc/os-release
nvidia-smi
command -v nvidia-container-runtime
nvidia-container-runtime --version
```

Keep driver/toolkit management with the supported DGX OS lifecycle. If the GPU or
runtime check fails, fix the host baseline using NVIDIA's guidance before adding
Kubernetes. Back up any existing K3s configuration. Stop if another device plugin,
GPU Operator, NFD, or an active host workload already owns the GPU; reconcile
ownership rather than installing duplicates.

## 2. Configure/install K3s deliberately

Review [K3s installation](https://docs.k3s.io/quick-start) and the
[version record](versions.md). Merge the entries from
`dgx-spark/gitops/bootstrap/k3s-config.yaml` into
`/etc/rancher/k3s/config.yaml` using your editor; **do not overwrite existing
settings**. Ensure the NVIDIA runtime is in the K3s service PATH before startup.

For a new lab only, download and review the official installer before executing
it. Run from an ignored temporary directory, not from a checked-in script:

```sh
mkdir -p .cache/bootstrap
curl -fsSLo .cache/bootstrap/install-k3s.sh https://get.k3s.io
# Inspect this downloaded installer before the next step.
INSTALL_K3S_VERSION='v1.34.12+k3s1' sh .cache/bootstrap/install-k3s.sh
```

The installer changes the host, starts K3s, and may request administrative
privileges. If K3s already exists, plan its upgrade/restart separately; do not
blindly rerun an installer or replace a working version. Runtime discovery occurs
on startup/restart. Inspect generated configuration read-only:

```sh
sudo grep nvidia /var/lib/rancher/k3s/agent/etc/containerd/config.toml
sudo k3s kubectl get nodes -o wide
sudo k3s kubectl get runtimeclass nvidia
```

Configure `kubectl`/Helm using a protected kubeconfig **outside this repository**
following [K3s cluster access](https://docs.k3s.io/cluster-access). Keep permissions
`0600`; do not make it world-readable. Do not print or paste its contents into Git
or chat. Check the current context before every apply/install:

```sh
kubectl config current-context
kubectl get nodes -o wide
```

## 3. Install pinned Argo CD once

Use the trusted Helm distribution, then install the pinned non-HA lab chart:

```sh
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update argo
helm upgrade --install argocd argo/argo-cd \
  --version 10.10.1 --namespace argocd --create-namespace \
  -f dgx-spark/gitops/bootstrap/argocd-values.yaml --wait --timeout 10m
kubectl -n argocd get pods
kubectl get crd applications.argoproj.io appprojects.argoproj.io
kubectl -n argocd port-forward --address 127.0.0.1 svc/argocd-server 8080:443
```

Open `https://localhost:8080`. Argo's default local certificate may not be trusted;
configure a trusted certificate or use an approved local-client workflow rather
than weakening server TLS or publicly exposing the UI. Authenticate locally using
Argo's official initial-login instructions, change the initial administrator
password, and keep it outside Git. This project intentionally does not print,
capture, or commit the initial credential.

The bootstrap is admin-privileged and non-HA. Before multi-user use, configure SSO,
explicit admin mappings, certificate management, backups, and appropriate Argo
RBAC. The example's default authenticated role is read-only.

## 4. Register projects/namespaces/root

Review `projects.yaml`; the root is an admin capability and infrastructure
operators need cluster permissions. Review namespace policies: GPU/network
operators and the host-metrics exporter require privileged namespaces, while
`ai-lab` uses the baseline policy. This is not an untrusted-tenant cluster.

For a fork, change the Git URL in root, workload project, bootstrap project, and
platform values together. The public upstream needs no Git credentials. If you
use a private fork, configure repository access directly in Argo/external secret
management; never add a token to a URL or manifest.

```sh
python dgx-spark/gitops/tools/validate.py --helm helm
kubectl apply -f dgx-spark/gitops/bootstrap/namespaces.yaml
kubectl apply -f dgx-spark/gitops/bootstrap/projects.yaml
kubectl apply -f dgx-spark/gitops/bootstrap/root-application.yaml
kubectl -n argocd get applications
```

Expected: parent plus two children. Workload defaults reconcile automatically;
GPU Operator should be registered but **OutOfSync** until manually synced. In the
Argo UI review the GPU Operator diff and disabled host-driver/toolkit/CDI/DCGM
settings, then sync only `dgx-gpu-operator` without pruning.

```sh
kubectl -n gpu-operator get pods
kubectl get clusterpolicy
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu
```

Expect one allocatable GPU on the intended Spark. Argo `Healthy`/`Synced` does not
prove CUDA computation or inference. Continue through the validation gates.
