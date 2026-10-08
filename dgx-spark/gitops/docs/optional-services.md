# Optional services

All optional children start disabled. Enable one at a time through a reviewed Git
change, inspect the Argo diff, and manually sync those marked manual. A parent
`Synced` state does not prove child readiness or dependency ordering.

## LiteLLM gateway

The gateway is an alias/router for the already-tested `model-service`, not an
inference engine. Its root-chart gate requires the model child enabled and matching
`servedModelName` values. Select an inspected ARM64 LiteLLM image digest exposing
the `litellm` executable. It must support the documented config and health paths.

Before syncing, create an authentication Secret in `ai-lab` **outside Git** using
your secret manager or a protected local file. The Secret name is `litellm-auth`
unless changed; required key: `LITELLM_MASTER_KEY`. Use a strong unique key with
the prefix expected by the selected LiteLLM version. Do not place the actual key
in platform values, command-line literals, this documentation, screenshots, or
commit history. Kubernetes Secret encoding alone is not encryption at rest.

Set `model-gateway.values.image`, enable it, validate, commit/push, then manually
sync `dgx-model-gateway`. Access it via a loopback port-forward:

```sh
kubectl -n ai-lab port-forward --address 127.0.0.1 svc/model-gateway 4000:4000
```

Test `/v1/chat/completions` using your local client with the gateway master key
provided securely at runtime. Check that a request **without** a key is rejected,
then verify an authenticated request returns a real response. Probe endpoints
`/health/liveliness` and `/health/readiness` are unauthenticated process checks;
they are not inference tests. Avoid logging authorization headers/private prompts.

The local backend's `api_key: unused-local-backend` is an inert SDK placeholder,
not a credential: the raw lab model is unauthenticated. NetworkPolicies narrow
normal ingress, not administrator/host access. Do not treat this gateway as a
multi-tenant security boundary or publish the backend.

This minimal gateway has **no PostgreSQL, virtual keys, user database, budgets,
or billing**. LiteLLM virtual keys require PostgreSQL and an independently managed
database credential, persistence, migrations, and tested backups. Add that as a
separate reviewed design rather than enabling database-dependent features here.

## Monitoring

Enable `monitoring` only after checking its chart/images on ARM64 and available
memory/disk. The pinned kube-prometheus-stack is tuned for a lab: Grafana and
Alertmanager off, 24-hour/4 GB retention cap, an 8 GiB local-path PVC, and disabled
scrapes for k3s components that may not expose standalone endpoints. CoreDNS
scraping is disabled to avoid creating a Service in `kube-system`, outside this
Application's allowed destination namespace.

Manually sync `dgx-monitoring`. Server-side apply is selected to handle large
operator CRDs. Wait for the Prometheus Operator, CRDs, and Prometheus to become
ready before adding any custom ServiceMonitor resources. This example uses a
static scrape target for the model's `/metrics`, so no model ServiceMonitor needs
to race CRD installation. Missing model targets are expected before model serving.

```sh
kubectl get crd prometheuses.monitoring.coreos.com servicemonitors.monitoring.coreos.com
kubectl -n monitoring get pods,svc,pvc
```

Find the actual Prometheus Service name in that output and port-forward it on
loopback. Check host memory/disk, Pod health, model request latency/errors and
queue metrics exposed by the chosen engine. Metric names and GPU-memory reporting
vary by version. Do not label host unified memory as dedicated VRAM.

There is no DCGM GPU dashboard by default. Verify the chosen GB10/DCGM exporter
release first if adding one. PVCs preserve local metrics across some restarts,
not a node failure or a backup. Grafana authentication would require externally
managed credentials if you enable Grafana later; none are committed here.

## Accelerated networking

Single-node HTTP model serving does **not** need NVIDIA Network Operator.
The disabled child pins the operator chart but deliberately installs no
`NicClusterPolicy` or OFED/RDMA settings. Enabling it is only operator registration,
not working accelerated networking or multi-node inference.

Check ConnectX hardware, firmware, host networking ownership, kernel/OFED support,
ARM64 images and the selected Network Operator platform matrix. Replacing a
network driver may disrupt management connectivity. Keep this manual and use a
separate maintenance/recovery plan; do not deploy it merely to copy a dashboard.
NFD, SR-IOV, and maintenance-operator dependencies are disabled here to avoid
unreviewed extra operators or duplicate NFD ownership.

## Sources

- [LiteLLM config](https://docs.litellm.ai/docs/proxy/configs)
- [LiteLLM health paths](https://docs.litellm.ai/docs/proxy/health)
- [LiteLLM virtual keys and PostgreSQL](https://docs.litellm.ai/docs/proxy/virtual_keys)
- [Prometheus chart documentation](https://github.com/prometheus-community/helm-charts/tree/kube-prometheus-stack-92.1.1/charts/kube-prometheus-stack)
- [Network Operator documentation](https://docs.nvidia.com/networking/software/cloud-orchestration.html)
