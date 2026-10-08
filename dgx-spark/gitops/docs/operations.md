# Git changes, shutdown, and recovery exercises

Work in a disposable trusted lab. Back up data independently before destructive
tests. Record exact Git SHA, chart pins, image digests, model revision, and real
test results. Do not commit credentials or private runtime evidence.

## Configuration and drift exercise

1. Choose a harmless non-secret change, such as a workload-default memory request.
2. Render, run the offline validation command, and review the Git diff.
3. Commit/push the change; watch desired/live comparison and automatic sync.
4. For an automatic child, deliberately change that live value in the lab. Observe
   self-heal restoring Git. Use a reviewed Git change for a lasting modification.
5. Revert your Git commit and push it. Confirm the configuration returns; if a
   model changed, repeat the real request test.

Only root/defaults/model children are automatic by default. GPU, checks, gateway,
monitoring, and network changes still need a deliberate manual sync. Review the
actual rendered child `syncPolicy`, not only the parent badge.

## Pruning and disabling are different

All automatic policies have `prune: false`; no application has a cascade-delete
finalizer. Removing a manifest from Git leaves its live object in place.
Likewise, `enabled: false` in platform values means **do not render this child**;
it does **not** shut down a previously-created child or its workloads. An old
model Application can continue automatically syncing even after disappearing
from the root's desired render.

To pause an existing model safely:

1. Keep its child `enabled: true`, change its `autoSync: false` in Git, and push.
2. Wait for root reconciliation and confirm the child's automatic sync is off.
3. Deliberately scale the model Deployment to zero in the lab. It should remain
   at zero while the child is manual; do not manually sync it during the pause.
4. If permanently removing it, disable the child in Git, wait for the root to
   reconcile, and remove that orphan Application **without cascading deletion**.
   Then review remaining workload objects and remove only intended resources.
5. Preserve the PVC/backups unless you explicitly intend to discard model data.

Changing child automation only in the UI is temporary while the root self-heals;
make the change in Git. For an emergency use the documented Argo pause procedure
for parent and child, verify it took effect, then perform the lab action. Never
assume a UI checkbox defeats a parent controller indefinitely.

For a desired shutdown that should reconcile from Git, extend the model contract
with a reviewed zero-replica maintenance setting and tests; do not enable a second
GPU replica. This initial contract deliberately enforces one serving replica.

Prune manually only after reviewing the deletion set. `PruneLast=true` only changes
ordering **when** pruning is explicitly requested; it does not turn pruning on.
PVCs have `Prune=false,Delete=false` as additional retention safeguards, not a
guarantee against administrator deletion, storage reclaim policy, or disk failure.

## Recovery exercises

### Rebuild configuration

For a genuinely empty replacement lab, repeat bootstrap, verify host stack and
runtime, and apply the root. Argo reconstructs configuration, not credentials,
model/data caches, prior Job evidence, or database contents. Recreate external
Secrets through their manager and restore data from independently stored backups.

### Service restart

Use disposable state and account for downtime. Verify PVC use, check actual
endpoints and a completion after replacement. Kubernetes `Recreate` avoids rollout
surge but does not absolutely serialize all manually deleted/terminating Pods.
One-GPU reservation does not protect against host-side competitors.

### Backup/restore

Back up a small non-sensitive test dataset to storage independent of the Spark.
Restore it into a separate test location and compare integrity checks. Document
what is backed up (configuration, application data, credentials through their
manager), encryption/access, retention, and tested restore steps. Local-path PVC
storage is node/disk-bound; a volume existing is not evidence of recoverability.
Do not test disaster recovery by deleting the only copy of any real data.

### Rollback boundaries

Git revert restores desired configuration. It cannot undo a database migration,
restore deleted files, recreate lost credentials, or make a changed model-cache
format compatible. Check those independently before promoting a release.

## Primary references

- [Automatic sync, self-heal and pruning](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [App-of-apps admin trust](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/#app-of-apps-pattern-alternative)
- [PVC retention sync options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)
- [Job TTL behavior](https://kubernetes.io/docs/concepts/workloads/controllers/ttlafterfinished/)
- [Recreate strategy caveats](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#recreate-deployment)
- [K3s backup/restore](https://docs.k3s.io/datastore/backup-restore)
