# Version and compatibility record

Checked against primary release/chart sources on **2026-10-08**. These are
example pins, not a claim that this combination has been run on your hardware.
Review security advisories and support windows before installation/upgrades.

| Component | Pin | Basis |
| --- | --- | --- |
| K3s | `v1.34.12+k3s1` | Published release; Kubernetes 1.34 is inside the GPU Operator platform range and Argo CD 3.5 tested range |
| Argo CD Helm chart | `10.10.1` | Chart's app version is `v3.5.4` |
| NVIDIA GPU Operator chart | `v26.7.1` | Exact published NVIDIA chart; Spark explicitly listed in ARM support matrix |
| Optional kube-prometheus-stack | `92.1.1` | Exact community chart release; defaults tuned down for this lab |
| Optional Network Operator chart | `26.7.0` | Exact NVIDIA Helm index entry; **no `v` prefix** in chart version |
| Local offline Helm rendering | `3.19.0` | Pinned renderer; no cluster connection required |
| Offline YAML parser | `PyYAML==6.0.3` | Only local validation dependency |

K3s and NVIDIA platform documentation use minor-version support ranges; they do
not certify every patch/image combination. The chart's Helm metadata is also
not a hardware test. Record the actual DGX OS, kernel, host driver/toolkit,
containerd, chart, operand images, workload image digests, and model revisions
in your lab notes before declaring a baseline working.

## Spark GPU path

This example intentionally uses the legacy NVIDIA runtime, not CDI:

```yaml
# Host K3s configuration
default-runtime: nvidia

# GPU Operator child values
driver: {enabled: false}
toolkit: {enabled: false}
cdi: {enabled: false}
dcgm: {enabled: false}
dcgmExporter: {enabled: false}
operator: {runtimeClass: nvidia}
```

Keep the supported Spark host driver/toolkit. K3s finds the installed runtime in
its service PATH at startup; it provides the `nvidia` RuntimeClass. Do not add a
second RuntimeClass owner or hand-edit its generated containerd configuration.
Do not copy the old generic 515-driver installation example onto Spark.

GPU Operator 26.7 supports Spark; disabling DCGM here follows the blog's
conservative baseline and is **not** a claim that every current telemetry
version is unsupported. Verify GB10 telemetry independently before enabling it.
GPU Operator owns node feature discovery; the optional Network Operator has NFD
disabled to avoid duplicate ownership.

## Workload pins are deliberately not invented

The official Spark guide uses
`nvcr.io/nvidia/cuda:13.0.1-devel-ubuntu24.04` for a device check. It is a candidate
for the validation chart, not a hard-coded image digest in this repo. Inspect
the registry manifest for `linux/arm64`, record its digest, then actually run
the CUDA computation gate. A successful pull or `nvidia-smi` is insufficient.

The model chart expects an image exposing `vllm serve`, supporting ARM64 and
GB10, with a tested model at a 40-character repository commit. The gateway
expects an ARM64 image exposing the `litellm` executable. Both require inspected
SHA-256 image references before rendering. Select images from their official
projects and verify compatibility, license, provenance, and vulnerability scans.
If an image uses a different entrypoint, adjust the contract and tests explicitly.
Do not assume generic x86 CUDA or vLLM images work on Spark.

Third-party charts pin component tags through their release defaults; tags can
still be mutable. For stronger reproducibility, capture chart package hashes and
actual image digests in the lab release record or mirror approved artifacts.
Git sources follow `main` intentionally so reviewed Git changes reconcile;
record the exact synced Git SHA for each exercise.

## Primary sources

- [K3s release](https://github.com/k3s-io/k3s/releases/tag/v1.34.12%2Bk3s1)
- [K3s alternative runtimes](https://docs.k3s.io/advanced#nvidia-container-runtime)
- [Argo CD tested Kubernetes versions](https://argo-cd.readthedocs.io/en/stable/operator-manual/installation/#tested-versions)
- [Pinned Argo chart](https://github.com/argoproj/argo-helm/blob/argo-cd-10.10.1/charts/argo-cd/Chart.yaml)
- [NVIDIA 26.7 platform matrix](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/platform-support.html)
- [GPU Operator installation](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/getting-started.html)
- [Pinned GPU chart values](https://github.com/NVIDIA/gpu-operator/blob/v26.7.1/deployments/gpu-operator/values.yaml)
- [Spark NGC guide](https://docs.nvidia.com/dgx/dgx-spark/ngc.html)
- [Spark porting requirements](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/porting/software-requirements.html)
- [Pinned Prometheus chart](https://github.com/prometheus-community/helm-charts/blob/kube-prometheus-stack-92.1.1/charts/kube-prometheus-stack/Chart.yaml)
- [Pinned Network Operator chart](https://github.com/Mellanox/network-operator/blob/v26.7.0/deployment/network-operator/Chart.yaml)
- [NVIDIA Helm index](https://helm.ngc.nvidia.com/nvidia/index.yaml)
