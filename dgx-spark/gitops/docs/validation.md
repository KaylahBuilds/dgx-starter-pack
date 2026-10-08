# Validate before model serving

Record real results privately. Nothing in this repository proves the GPU Jobs or
inference have run. Stop at the first failed gate; do not skip directly to model
deployment because the Argo dashboard is green.

## Gate 1: host, runtime, and allocation

After [bootstrap](bootstrap.md), verify:

```sh
nvidia-smi
kubectl get runtimeclass nvidia
kubectl -n gpu-operator get pods
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu
```

Expect an ARM64 Spark with one allocatable GPU. The host must already have a
working supported driver/toolkit. Do not enable MIG/time-slicing in this example.
The scheduler's GPU reservation does not exclude native/Docker processes on the
host: stop competing workloads deliberately, with their owners' approval.

## Gate 2: inspect and pin a CUDA image

Use the official Spark candidate only after checking the registry manifest:

```sh
docker buildx imagetools inspect nvcr.io/nvidia/cuda:13.0.1-devel-ubuntu24.04
```

Confirm `linux/arm64`, capture the registry digest, and inspect provenance and
driver/CUDA compatibility. An immutable multi-platform index digest is acceptable
if it includes the correct ARM64 image. Authentication, if required, stays in your
local registry login/externally managed pull Secret, never Git. Workload images in
this example are expected to be accessible without a committed pull credential.

In `platform/values.yaml`, set `gpu-validation.values.image` to the inspected
`registry/repository@sha256:…` reference, choose a new `runId`, and enable the child.
Run the offline checks, review the non-secret diff, then commit/push it. The root
creates the child; manually review and sync `dgx-gpu-validation` without pruning.

```sh
kubectl -n ai-lab get jobs
kubectl -n ai-lab logs job/gpu-visibility-rc1
kubectl -n ai-lab logs job/gpu-compute-rc1
```

Substitute your actual run ID. Visibility must print the expected GPU, and compute
must finish successfully with `PASS: 256 CUDA arithmetic results verified`.
The compute Job compiles with `nvcc -arch=native` in the selected devel image and
checks 256 GPU-produced results. Failures in compilation/device execution stop
the gate. This is a tiny compatibility test, **not** a model or throughput test.

Jobs have `backoffLimit: 0`, a deadline, and no automatic TTL. The visibility Job
finishes before the compute wave, releasing its GPU. Keep the completed Jobs as
evidence. For a rerun or immutable Pod-template change, use a **new run ID** so
both Job and ConfigMap names change. Do not force-replace old Jobs as a shortcut.

With no pruning, old Jobs remain. When no longer needed, remove them from the
desired render, inspect what is no longer desired, and deliberately clean only
those old Jobs/ConfigMaps. Never delete a still-desired Job under self-healing
and expect it to stay deleted.

## Gate 3: verify a model outside Kubernetes first

Choose a small model and an official serving image with explicit ARM64/GB10
support. Verify its command, `/health`, `/v1/models`, `/v1/chat/completions`, and
`/metrics` interfaces. Test a real request on the Spark's supported container
runtime before using the Kubernetes chart. Record the immutable image digest and
40-character model repository revision, license, context limit, host memory,
disk use, and measured behavior. Do not automatically trust remote model code.

Then edit `model-service.values` in platform values:

- `image`: verified serving image digest, not `latest` or an uninspected tag.
- `modelId` and `modelRevision`: tested accessible repository and immutable commit.
- `command`: default `vllm serve`; change explicitly for your tested image if needed.
- CPU/memory/cache limits: measure them; the illustrative 32 GiB limit is not a
  promise a chosen model will fit. Unified memory and host overhead both matter.
- `extraArgs`: documented non-secret tuning flags such as a measured context or
  serving memory setting. Contract overrides, credentials and remote-code flags
  are rejected; gated model authentication needs a separate reviewed Secret design.

Enable `model-service`, validate the chart, review the diff, and commit/push.
Its automatic sync uses **one replica, one GPU, `Recreate`**, intentionally with
update downtime. Finish GPU validation first. When the Deployment is ready:

```sh
kubectl -n ai-lab get deployment model-service
kubectl -n ai-lab get pods,pvc
kubectl -n ai-lab port-forward --address 127.0.0.1 svc/model-service 8000:8000
```

From a separate terminal on the same host:

```sh
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/v1/models
curl --fail http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"spark-model","messages":[{"role":"user","content":"Reply with a short greeting."}],"max_tokens":32}'
```

Use the selected `servedModelName` if you changed it. Confirm a real completion,
not just an HTTP listener. Record latency, errors, host memory, Pod memory, and
disk. Readiness probes show service health, not answer quality or complete
end-to-end availability. Port-forward is local/admin access; do not expose the
unauthenticated backend outside the trusted lab.

The model's cache is local-path storage. Pod replacement may retain it; node/disk
failure may not. A model-image rollback cannot undo a data-format migration.

## Failure triage

| Symptom | First checks |
| --- | --- |
| `Pending`, insufficient GPU | Prior GPU Jobs still active, another model Pod, device-plugin allocation, sharing settings |
| Runtime handler missing | Host NVIDIA runtime in service PATH, restart plan, generated containerd config and RuntimeClass |
| `exec format error` | Registry manifest architecture and selected digest |
| CUDA/no kernel image error | Driver/CUDA/GB10 support; passing `nvidia-smi` alone proves too little |
| Job immutable-field error | New run ID, not force-replacement |
| `ImagePullBackOff` | Digest, registry reachability, externally managed login/pull credentials |
| Model crashes/OOM | Unified-memory pressure, measured context/engine settings, Pod limit, host workloads |
| PVC pending/full | local-path provisioner, node affinity, disk capacity; not a GPU issue |
| Argo PermissionDenied | Correct project, allowed source/destination/kind; do not grant wildcard workload permissions |

Inspect events/logs without publishing credentials, private prompts, or datasets.
Never commit full environment dumps or kubeconfigs as troubleshooting evidence.
