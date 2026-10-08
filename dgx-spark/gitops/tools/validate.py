"""Offline render checks for the DGX Spark GitOps example.

Requires PyYAML and a separately installed Helm CLI. This script only renders
local charts and reads files; it never contacts Kubernetes or deploys resources.
Synthetic image/model pins used in tests are not deployable recommendations.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import shutil
import subprocess
import tempfile

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
GITOPS_ROOT = REPO_ROOT / "dgx-spark" / "gitops"
FAKE_IMAGE = "example.invalid/arm64-study@sha256:" + "a" * 64
FAKE_MODEL_REVISION = "b" * 40


def load_documents(path: Path) -> list[dict]:
    """Load concrete YAML manifests, rejecting non-object documents."""
    documents = [item for item in yaml.safe_load_all(path.read_text(encoding="utf-8")) if item is not None]
    if any(not isinstance(item, dict) for item in documents):
        raise ValueError(f"Expected YAML object documents: {path}")
    return documents


def load_values(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a values object: {path}")
    return value


def baseline_values() -> dict:
    return load_values(GITOPS_ROOT / "platform" / "values.yaml")


def synthetic_values() -> dict:
    """Enable optional children using deliberately non-deployable fake pins."""
    values = deepcopy(baseline_values())
    for app in values["applications"].values():
        app["enabled"] = True
    for name in ["gpu-validation", "model-service", "model-gateway"]:
        values["applications"][name]["values"]["image"] = FAKE_IMAGE
    values["applications"]["model-service"]["values"].update(
        modelId="synthetic/example", modelRevision=FAKE_MODEL_REVISION
    )
    return values


def render_chart(helm: str, path: Path, values: dict | None = None, namespace: str = "ai-lab") -> subprocess.CompletedProcess:
    """Run Helm template locally, with test fixtures under the ignored cache."""
    cache = REPO_ROOT / ".cache" / "gitops-validation"
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="render-", dir=cache) as temporary:
        command = [helm, "template", "dgx-offline-test", str(path), "--namespace", namespace]
        if values is not None:
            value_file = Path(temporary) / "values.yaml"
            value_file.write_text(yaml.safe_dump(values, sort_keys=False), encoding="utf-8")
            command.extend(["--values", str(value_file)])
        return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=30, check=False)


def rendered_documents(result: subprocess.CompletedProcess) -> list[dict]:
    if result.returncode:
        raise AssertionError(f"Helm rendering failed:\n{result.stderr}")
    documents = [item for item in yaml.safe_load_all(result.stdout) if item is not None]
    if any(not isinstance(item, dict) for item in documents):
        raise AssertionError("Helm output contained a non-object YAML document")
    return documents


def find_resource(documents: list[dict], kind: str, name: str | None = None) -> dict:
    matches = [doc for doc in documents if doc.get("kind") == kind and (name is None or doc["metadata"]["name"] == name)]
    if len(matches) != 1:
        raise AssertionError(f"Expected exactly one {kind} {name or ''}; got {len(matches)}")
    return matches[0]


def api_group(api_version: str) -> str:
    return api_version.split("/", 1)[0] if "/" in api_version else ""


def project_allows_manifest(project: dict, manifest: dict, namespace: str) -> bool:
    """Check this example's namespaced kind allowlist, not cluster admission."""
    destination_allowed = any(
        destination["server"] == "https://kubernetes.default.svc" and destination["namespace"] == namespace
        for destination in project["spec"]["destinations"]
    )
    manifest_namespace = manifest.get("metadata", {}).get("namespace", namespace)
    kind_allowed = any(
        entry["group"] in {"*", api_group(manifest["apiVersion"])} and entry["kind"] in {"*", manifest["kind"]}
        for entry in project["spec"].get("namespaceResourceWhitelist", [])
    )
    return destination_allowed and manifest_namespace == namespace and kind_allowed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helm", default=shutil.which("helm"), help="Path to Helm; no tools are downloaded automatically.")
    args = parser.parse_args()
    if not args.helm:
        parser.error("Helm is required. Supply --helm /absolute/path/to/helm.")

    import unittest
    import test_validate

    test_validate.HELM_EXECUTABLE = args.helm
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_validate.GitOpsStaticTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print("Static rendering only: no cluster contacted, no deployment or DGX runtime compatibility verified.")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
