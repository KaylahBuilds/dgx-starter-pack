"""Static GitOps tests. Synthetic pins are test fixtures, never runnable images."""

from __future__ import annotations

import argparse
from copy import deepcopy
import os
import re
import shutil
import sys
import unittest

from validate import (
    FAKE_IMAGE,
    FAKE_MODEL_REVISION,
    GITOPS_ROOT,
    baseline_values,
    find_resource,
    load_documents,
    load_values,
    project_allows_manifest,
    render_chart,
    rendered_documents,
    synthetic_values,
)


HELM_EXECUTABLE = os.environ.get("DGX_LAB_HELM") or shutil.which("helm")


class GitOpsStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HELM_EXECUTABLE:
            raise RuntimeError("Helm is required; run validate.py --helm /absolute/path/to/helm.")
        cls.helm = HELM_EXECUTABLE
        cls.baseline = baseline_values()
        cls.synthetic = synthetic_values()
        cls.projects = {item["metadata"]["name"]: item for item in load_documents(GITOPS_ROOT / "bootstrap" / "projects.yaml")}
        cls.default_children = rendered_documents(render_chart(cls.helm, GITOPS_ROOT / "platform", namespace="argocd"))
        cls.all_children = rendered_documents(render_chart(cls.helm, GITOPS_ROOT / "platform", cls.synthetic, namespace="argocd"))
        cls.children_by_name = {child["metadata"]["name"]: child for child in cls.all_children}
        cls.local_documents = {}
        for app_name in ["gpu-validation", "model-service", "model-gateway"]:
            app = cls.synthetic["applications"][app_name]
            chart = GITOPS_ROOT.parents[1] / app["path"]
            cls.local_documents[app_name] = rendered_documents(render_chart(cls.helm, chart, app["values"]))

    def chart_result(self, name: str, values: dict | None = None):
        app = self.synthetic["applications"][name]
        chart = GITOPS_ROOT.parents[1] / app["path"]
        return render_chart(self.helm, chart, values if values is not None else app["values"])

    def assert_render_fails(self, result, message: str):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)

    def test_baseline_registers_only_two_children(self):
        self.assertEqual({child["metadata"]["name"] for child in self.default_children}, {"dgx-gpu-operator", "dgx-workload-defaults"})
        self.assertTrue(all(child["kind"] == "Application" for child in self.default_children))
        operator = find_resource(self.default_children, "Application", "dgx-gpu-operator")
        self.assertNotIn("automated", operator["spec"]["syncPolicy"])
        operator_values = operator["spec"]["source"]["helm"]["valuesObject"]
        for component in ("driver", "toolkit", "cdi", "dcgm", "dcgmExporter"):
            self.assertFalse(operator_values[component]["enabled"])
        self.assertEqual(operator_values["operator"]["runtimeClass"], "nvidia")
        defaults = find_resource(self.default_children, "Application", "dgx-workload-defaults")
        self.assertFalse(defaults["spec"]["syncPolicy"]["automated"]["prune"])

    def test_optionals_are_disabled_before_opt_in(self):
        for name in ["gpu-validation", "model-service", "model-gateway", "monitoring", "accelerated-networking"]:
            self.assertFalse(self.baseline["applications"][name]["enabled"])

    def test_synthetic_all_optionals_render_seven_children(self):
        self.assertEqual(len(self.all_children), 7)
        self.assertEqual({child["metadata"]["name"] for child in self.all_children}, {"dgx-" + name for name in self.synthetic["applications"]})

    def test_app_project_repositories_and_destinations(self):
        for child in self.all_children:
            spec = child["spec"]
            project = self.projects[spec["project"]]["spec"]
            self.assertIn(spec["source"]["repoURL"], project["sourceRepos"])
            self.assertIn(spec["destination"], project["destinations"])
            self.assertEqual(child["metadata"]["namespace"], "argocd")
            self.assertNotIn("finalizers", child["metadata"])

    def test_root_automatic_registration_without_pruning_or_cascade(self):
        root = load_documents(GITOPS_ROOT / "bootstrap" / "root-application.yaml")[0]
        self.assertEqual(root["spec"]["project"], "dgx-bootstrap")
        self.assertEqual(root["spec"]["destination"]["namespace"], "argocd")
        self.assertEqual(root["spec"]["syncPolicy"]["automated"], {"enabled": True, "selfHeal": True, "prune": False})
        self.assertNotIn("finalizers", root["metadata"])

    def test_projects_keep_parent_privileged_and_workloads_scoped(self):
        parent = self.projects["dgx-bootstrap"]["spec"]
        workload = self.projects["dgx-workloads"]["spec"]
        self.assertEqual(parent["clusterResourceWhitelist"], [])
        self.assertEqual(parent["namespaceResourceWhitelist"], [{"group": "argoproj.io", "kind": "Application"}])
        self.assertEqual(workload["clusterResourceWhitelist"], [])
        self.assertNotIn("Secret", {item["kind"] for item in workload["namespaceResourceWhitelist"]})
        self.assertNotIn("Namespace", {item["kind"] for item in workload["namespaceResourceWhitelist"]})
        self.assertEqual({item["namespace"] for item in workload["destinations"]}, {"ai-lab"})

    def test_local_resource_kinds_fit_workload_project(self):
        project = self.projects["dgx-workloads"]
        for name, manifests in self.local_documents.items():
            for manifest in manifests:
                with self.subTest(application=name, kind=manifest["kind"]):
                    self.assertTrue(project_allows_manifest(project, manifest, "ai-lab"))
        self.assertFalse(project_allows_manifest(project, {"apiVersion": "v1", "kind": "Secret", "metadata": {}}, "ai-lab"))

    def test_kustomization_resources_resolve_inside_the_defaults_directory(self):
        directory = GITOPS_ROOT / "workloads" / "defaults"
        kustomization = load_values(directory / "kustomization.yaml")
        self.assertEqual(kustomization["namespace"], "ai-lab")
        for name in kustomization["resources"]:
            path = (directory / name).resolve()
            self.assertTrue(path.is_relative_to(directory.resolve()))
            self.assertTrue(path.is_file())
            for manifest in load_documents(path):
                self.assertTrue(project_allows_manifest(self.projects["dgx-workloads"], manifest, "ai-lab"))
        service_account = load_documents(directory / "service-account.yaml")[0]
        self.assertFalse(service_account["automountServiceAccountToken"])

    def test_no_secret_templates_or_managed_secrets(self):
        for path in GITOPS_ROOT.rglob("*.yaml"):
            if "tools" not in path.parts:
                self.assertIsNone(re.search(r"(?m)^\s*kind:\s*Secret\s*$", path.read_text(encoding="utf-8")), str(path))
        for manifests in self.local_documents.values():
            self.assertTrue(all(item["kind"] != "Secret" for item in manifests))

    def test_chart_revisions_are_version_pins(self):
        for name, app in self.baseline["applications"].items():
            if app.get("chart"):
                self.assertRegex(app["revision"], r"^v?\d+\.\d+\.\d+$", name)
        self.assertFalse(self.baseline["applications"]["monitoring"]["values"]["coreDns"]["enabled"])

    def test_platform_rejects_unpinned_image(self):
        values = deepcopy(self.synthetic)
        values["applications"]["gpu-validation"]["values"]["image"] = "example.invalid/study:latest"
        self.assert_render_fails(render_chart(self.helm, GITOPS_ROOT / "platform", values), "image must be pinned")

    def test_platform_rejects_missing_model_revision(self):
        values = deepcopy(self.synthetic)
        values["applications"]["model-service"]["values"]["modelRevision"] = ""
        self.assert_render_fails(render_chart(self.helm, GITOPS_ROOT / "platform", values), "model revision")

    def test_gateway_requires_the_model_child(self):
        values = deepcopy(self.synthetic)
        values["applications"]["model-service"]["enabled"] = False
        self.assert_render_fails(render_chart(self.helm, GITOPS_ROOT / "platform", values), "model-service before model-gateway")

    def test_gateway_rejects_a_mismatched_served_model_name(self):
        values = deepcopy(self.synthetic)
        values["applications"]["model-gateway"]["values"]["servedModelName"] = "different-model"
        self.assert_render_fails(render_chart(self.helm, GITOPS_ROOT / "platform", values), "servedModelName must match")

    def test_local_charts_reject_missing_digest(self):
        for name in self.local_documents:
            values = deepcopy(self.synthetic["applications"][name]["values"])
            values["image"] = ""
            with self.subTest(application=name):
                self.assert_render_fails(self.chart_result(name, values), "Set image")

    def test_validation_job_gpu_runtime_and_lifecycle(self):
        jobs = [item for item in self.local_documents["gpu-validation"] if item["kind"] == "Job"]
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.assertEqual(job["spec"]["backoffLimit"], 0)
            self.assertLessEqual(job["spec"]["activeDeadlineSeconds"], 600)
            self.assertNotIn("ttlSecondsAfterFinished", job["spec"])
            pod = job["spec"]["template"]["spec"]
            self.assertEqual(pod["runtimeClassName"], "nvidia")
            self.assertEqual(pod["nodeSelector"]["kubernetes.io/arch"], "arm64")
            self.assertFalse(pod["automountServiceAccountToken"])
            self.assertEqual(pod["containers"][0]["resources"]["limits"]["nvidia.com/gpu"], 1)
            self.assertEqual(job["metadata"]["annotations"]["argocd.argoproj.io/sync-options"], "Prune=false")

    def test_validation_rejects_invalid_run_id(self):
        for run_id in ["Bad_ID", "a" * 25, "", "-bad", "bad-"]:
            values = deepcopy(self.synthetic["applications"]["gpu-validation"]["values"])
            values["runId"] = run_id
            with self.subTest(run_id=run_id):
                self.assert_render_fails(self.chart_result("gpu-validation", values), "runId")

    def test_model_single_gpu_recreate_private_service_and_retained_cache(self):
        documents = self.local_documents["model-service"]
        deployment = find_resource(documents, "Deployment", "model-service")
        self.assertEqual(deployment["spec"]["replicas"], 1)
        self.assertEqual(deployment["spec"]["strategy"]["type"], "Recreate")
        pod = deployment["spec"]["template"]["spec"]
        self.assertEqual(pod["runtimeClassName"], "nvidia")
        self.assertEqual(pod["nodeSelector"]["kubernetes.io/arch"], "arm64")
        self.assertFalse(pod["automountServiceAccountToken"])
        container = pod["containers"][0]
        self.assertEqual(container["resources"]["limits"]["nvidia.com/gpu"], 1)
        self.assertEqual(container["image"], FAKE_IMAGE)
        args = container["args"]
        self.assertEqual(args[args.index("--revision") + 1], FAKE_MODEL_REVISION)
        self.assertNotIn("--trust-remote-code", args)
        self.assertEqual(find_resource(documents, "Service", "model-service")["spec"]["type"], "ClusterIP")
        self.assertIn("Delete=false", find_resource(documents, "PersistentVolumeClaim", "model-cache")["metadata"]["annotations"]["argocd.argoproj.io/sync-options"])

    def test_model_rejects_missing_model_pin(self):
        values = deepcopy(self.synthetic["applications"]["model-service"]["values"])
        values["modelRevision"] = "main"
        self.assert_render_fails(self.chart_result("model-service", values), "modelRevision")

    def test_model_rejects_serving_contract_overrides(self):
        for argument in ["--revision=main", "--api-key=not-a-real-key", "--trust-remote-code", "--host=0.0.0.0"]:
            values = deepcopy(self.synthetic["applications"]["model-service"]["values"])
            values["extraArgs"] = [argument]
            with self.subTest(argument=argument):
                self.assert_render_fails(self.chart_result("model-service", values), "extraArgs")

    def test_gateway_uses_only_external_secret_auth_and_private_service(self):
        documents = self.local_documents["model-gateway"]
        deployment = find_resource(documents, "Deployment", "model-gateway")
        pod = deployment["spec"]["template"]["spec"]
        self.assertFalse(pod["automountServiceAccountToken"])
        self.assertEqual(pod["nodeSelector"]["kubernetes.io/arch"], "arm64")
        container = pod["containers"][0]
        auth = next(item for item in container["env"] if item["name"] == "LITELLM_MASTER_KEY")
        self.assertNotIn("value", auth)
        self.assertEqual(auth["valueFrom"]["secretKeyRef"]["key"], "LITELLM_MASTER_KEY")
        self.assertEqual(auth["valueFrom"]["secretKeyRef"]["name"], "litellm-auth")
        self.assertEqual(find_resource(documents, "Service", "model-gateway")["spec"]["type"], "ClusterIP")
        config = find_resource(documents, "ConfigMap", "model-gateway-config")["data"]["config.yaml"]
        self.assertIn("os.environ/LITELLM_MASTER_KEY", config)
        self.assertTrue(all(item["kind"] != "Secret" for item in documents))

    def test_network_policies_select_actual_workloads_and_limit_ingress_ports(self):
        for app_name, deployment_name, port in [("model-service", "model-service", 8000), ("model-gateway", "model-gateway", 4000)]:
            documents = self.local_documents[app_name]
            policy = find_resource(documents, "NetworkPolicy", deployment_name + "-ingress")
            deployment = find_resource(documents, "Deployment", deployment_name)
            labels = deployment["spec"]["template"]["metadata"]["labels"]
            self.assertEqual(policy["spec"]["podSelector"]["matchLabels"], labels)
            self.assertEqual(policy["spec"]["policyTypes"], ["Ingress"])
            for rule in policy["spec"]["ingress"]:
                self.assertTrue(rule["from"])
                self.assertEqual(rule["ports"], [{"protocol": "TCP", "port": port}])
                self.assertTrue(all(peer.get("podSelector", {}).get("matchLabels") for peer in rule["from"]))

    def test_services_target_the_matching_deployment_port(self):
        for app_name, deployment_name in [("model-service", "model-service"), ("model-gateway", "model-gateway")]:
            documents = self.local_documents[app_name]
            service = find_resource(documents, "Service", deployment_name)
            deployment = find_resource(documents, "Deployment", deployment_name)
            template = deployment["spec"]["template"]
            self.assertEqual(service["spec"]["selector"], template["metadata"]["labels"])
            available_ports = {item["name"] for container in template["spec"]["containers"] for item in container.get("ports", [])}
            for port in service["spec"]["ports"]:
                self.assertIn(port["targetPort"], available_ports)

    def test_bootstrap_keeps_tls_clusterip_and_private_kubeconfig(self):
        argo = load_values(GITOPS_ROOT / "bootstrap" / "argocd-values.yaml")
        self.assertFalse(argo["configs"]["params"]["server.insecure"])
        self.assertEqual(argo["server"]["service"]["type"], "ClusterIP")
        self.assertFalse(argo["server"]["ingress"]["enabled"])
        k3s = load_values(GITOPS_ROOT / "bootstrap" / "k3s-config.yaml")
        self.assertEqual(str(k3s["write-kubeconfig-mode"]), "0600")
        self.assertEqual(k3s["default-runtime"], "nvidia")
        self.assertNotIn("token", k3s)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument("--helm", help="Path to Helm; no tools are downloaded automatically.")
    options, remaining = parser.parse_known_args()
    if options.helm:
        HELM_EXECUTABLE = options.helm
    unittest.main(argv=[sys.argv[0], *remaining], verbosity=2)
