import ast
import configparser
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = ROOT / "install.sh"
APPLY_K8S_SH = ROOT / "k8s" / "apply-k8s.sh"
WEBAPP_DEPLOYMENT = ROOT / "k8s" / "webapp-deployment.yaml"
JENKINS_DEPLOYMENT = ROOT / "k8s" / "jenkins-deployment.yaml"
JUNOS_MCP_DEPLOYMENT = ROOT / "k8s" / "junos-mcp-deployment.yaml"
NITA_CI = ROOT / ".github" / "workflows" / "nita-ci.yaml"
JUNOS_MCP_CI = ROOT / ".github" / "workflows" / "build-junos-mcp.yaml"
GENERIC_PROJECT = ROOT / "utils" / "nitaprj" / "profiles" / "generic" / "project.yaml"
GENERIC_ANSIBLE_JOB = (
    ROOT
    / "utils"
    / "nitaprj"
    / "profiles"
    / "generic"
    / "create_ansible_job_k8s.py"
)


class InstallerRegressionTests(unittest.TestCase):
    def setUp(self):
        self.install_text = INSTALL_SH.read_text(encoding="utf-8")
        self.apply_text = APPLY_K8S_SH.read_text(encoding="utf-8")
        self.webapp_text = WEBAPP_DEPLOYMENT.read_text(encoding="utf-8")
        self.jenkins_text = JENKINS_DEPLOYMENT.read_text(encoding="utf-8")
        self.junos_mcp_text = JUNOS_MCP_DEPLOYMENT.read_text(encoding="utf-8")
        self.generic_project_text = GENERIC_PROJECT.read_text(encoding="utf-8")
        self.generic_ansible_job_text = GENERIC_ANSIBLE_JOB.read_text(
            encoding="utf-8",
        )

    def installer_function(self, name):
        match = re.search(
            rf"^{name}\(\) \{{\n.*?^\}}",
            self.install_text,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        return match.group()

    def test_package_commands_preserve_arguments_and_fail_on_unknown_os(self):
        functions = "\n".join(
            self.installer_function(name)
            for name in ("InstallPackages", "UpdatePackages")
        )
        for os_name, manager in (("AlmaLinux", "dnf"), ("Ubuntu", "apt")):
            with self.subTest(os=os_name):
                result = subprocess.run(
                    [
                        "bash", "-c",
                        functions + '\n'
                        'dnf() { printf "dnf <%s>\\n" "$@"; }\n'
                        'apt() { printf "apt <%s>\\n" "$@"; }\n'
                        'OS="$1"; InstallPackages "one package" '
                        '"literal;not-a-command" || exit; UpdatePackages',
                        "test", os_name,
                    ],
                    text=True, capture_output=True, check=True,
                )
                self.assertEqual(
                    result.stdout.splitlines(),
                    [f"{manager} <{arg}>" for arg in (
                        "install", "-y", "one package", "literal;not-a-command",
                        "update", "-y",
                    )],
                )
        result = subprocess.run(
            ["bash", "-c", functions + '\nOS=Other; ME=test; InstallPackages pkg'],
            text=True, capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported package manager", result.stderr)
        result = subprocess.run(
            [
                "bash", "-c",
                functions + '\ndnf() { return 37; }; OS=AlmaLinux; InstallPackages pkg',
            ],
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 37)

    def test_debug_does_not_execute_expanded_arguments_or_log_keypass(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "injected"
            argument = f"$(touch {marker})"
            result = subprocess.run(
                [
                    "bash", "-c",
                    self.installer_function("Debug")
                    + '\nDEBUG=1; ME=test; Debug echo "$1"',
                    "test", argument,
                ],
                text=True, capture_output=True, check=True,
            )
            self.assertIn(argument, result.stderr)
            self.assertFalse(marker.exists())
        self.assertNotRegex(self.install_text, r"(?m)^\s*Debug .*\$KEYPASS")
        self.assertNotRegex(self.install_text, r"(?m)^\s*eval(?:\s|$)")

    def test_ubuntu_installs_supported_openjdk_package(self):
        self.assertIn("openjdk-21-jre-headless", self.install_text)
        self.assertNotIn("openjdk-19-jre-headless", self.install_text)

    def test_jdk_19_java_home_is_not_global_default(self):
        self.assertNotIn(
            "JAVA_HOME=${JAVA_HOME:=$NITAROOT/jdk-19.0.1}",
            self.install_text,
        )

    def test_core_configmaps_are_created_before_core_apply(self):
        apply_pos = self.install_text.index("bash apply-k8s.sh")
        self.assertLess(self.install_text.index("prepare-traefik.sh"), apply_pos)
        for name in ("jenkins-crt", "jenkins-keystore"):
            create_pos = self.install_text.index(f"kubectl create cm {name}")
            self.assertLess(
                create_pos,
                apply_pos,
                msg=f"{name} must exist before deployments are applied",
            )

    def test_core_apply_excludes_optional_junos_mcp_manifests(self):
        for variable in ("BASE_FILES", "WORKLOAD_FILES"):
            files_match = re.search(
                rf'^{variable}="([^"]+)"',
                self.apply_text,
                re.MULTILINE,
            )
            self.assertIsNotNone(
                files_match,
                f"apply-k8s.sh should define {variable}",
            )
            files = files_match.group(1).split()
            self.assertNotIn("junos-mcp-deployment.yaml", files)
            self.assertNotIn("junos-mcp-service.yaml", files)

    def test_core_apply_preflights_required_configmaps(self):
        for name in (
            "nita-traefik-config",
            "nita-traefik-bodylimit",
            "nita-traefik-identityguard",
            "jenkins-crt",
            "jenkins-keystore",
        ):
            self.assertIn(name, self.apply_text)
        self.assertRegex(self.apply_text, r"kubectl get cm .*\$\{cm\}")
        self.assertIn("kubectl get secret nita-traefik-tls", self.apply_text)

    def test_public_ghcr_and_juniper_are_the_defaults(self):
        for script_text in (self.install_text, self.apply_text):
            self.assertIn(
                "CONTAINER_REGISTRY=${CONTAINER_REGISTRY:=ghcr.io/juniper}",
                script_text,
            )
            self.assertIn("GITHUB_ORG=${GITHUB_ORG:=Juniper}", script_text)
            self.assertNotIn("ghcr.io/aburston", script_text)

    def test_complete_image_defaults_preserve_caller_overrides(self):
        expected_defaults = {
            "NITA_WEBAPP_IMAGE": "nita-webapp",
            "NITA_JENKINS_IMAGE": "nita-jenkins",
            "NITA_ANSIBLE_IMAGE": "nita-ansible",
            "NITA_ROBOT_IMAGE": "nita-robot",
            "JUNOS_MCP_IMAGE": "junos-mcp-server",
        }
        for variable, repository in expected_defaults.items():
            assignment = (
                f"{variable}=${{{variable}:="
                f"${{CONTAINER_REGISTRY}}/{repository}:latest}}"
            )
            self.assertIn(assignment, self.install_text)
            self.assertIn(assignment, self.apply_text)

    def test_manifests_use_complete_image_references(self):
        self.assertIn("image: ${NITA_WEBAPP_IMAGE}", self.webapp_text)
        self.assertIn("image: ${NITA_JENKINS_IMAGE}", self.jenkins_text)
        self.assertIn("image: ${JUNOS_MCP_IMAGE}", self.junos_mcp_text)

        for text in (
            self.webapp_text,
            self.jenkins_text,
            self.junos_mcp_text,
        ):
            self.assertNotRegex(
                text,
                r"image: \$\{CONTAINER_REGISTRY\}/(?:nita-|junos-mcp)",
            )

    def test_installer_renders_optional_junos_mcp_image_before_apply(self):
        self.assertIn(
            "envsubst '${JUNOS_MCP_IMAGE}'",
            self.install_text,
        )
        self.assertNotIn("imagePullPolicy:", self.junos_mcp_text)
        self.assertNotIn(
            "kubectl apply -f ${K8SROOT}/junos-mcp-deployment.yaml",
            self.install_text,
        )

    def test_jenkins_receives_worker_image_references(self):
        for variable in ("NITA_ANSIBLE_IMAGE", "NITA_ROBOT_IMAGE"):
            self.assertRegex(
                self.jenkins_text,
                rf"- name: {variable}\s+value: \"\$\{{{variable}\}}\"",
            )
            self.assertIn(variable, self.apply_text)

    def test_generic_project_uses_jenkins_worker_image_environment(self):
        self.assertNotIn(
            "juniper/nita-ansible",
            self.generic_project_text,
        )
        self.assertNotIn(
            "juniper/nita-robot",
            self.generic_project_text,
        )
        self.assertIn(
            "NITA_ANSIBLE_IMAGE",
            self.generic_ansible_job_text,
        )
        self.assertIn(
            "ghcr.io/juniper/nita-ansible:latest",
            self.generic_ansible_job_text,
        )

    def test_complete_tag_and_digest_examples_remain_verbatim(self):
        rendered_webapp = self.webapp_text.replace(
            "${NITA_WEBAPP_IMAGE}",
            "registry.example/team/webapp:validation",
        )
        rendered_jenkins = self.jenkins_text.replace(
            "${NITA_JENKINS_IMAGE}",
            "ghcr.io/juniper/nita-jenkins@sha256:deadbeef",
        )
        self.assertIn(
            "image: registry.example/team/webapp:validation",
            rendered_webapp,
        )
        self.assertIn(
            "image: ghcr.io/juniper/nita-jenkins@sha256:deadbeef",
            rendered_jenkins,
        )

    def test_fork_ci_builds_latest_webapp_main_and_gates_upstream_arm_runner(self):
        workflow = NITA_CI.read_text(encoding="utf-8")
        self.assertIn("format('{0}/nita-webapp', github.repository_owner)", workflow)
        self.assertIn("vars.NITA_WEBAPP_SOURCE_REPOSITORY", workflow)
        self.assertIn("vars.NITA_WEBAPP_SOURCE_REF", workflow)
        self.assertIn("vars.NITA_WEBAPP_SOURCE_REF || 'main'", workflow)
        self.assertNotRegex(workflow, r"WEBAPP_REF:.*'[0-9a-f]{40}'")
        e2e_workflow = workflow.split("  e2e-kind:", 1)[1]
        self.assertNotIn("ghcr.io/juniper/nita-webapp:latest", e2e_workflow)
        self.assertIn("ghcr.io/juniper/nita-jenkins:latest", workflow)
        self.assertIn("ghcr.io/juniper/nita-ansible:latest", workflow)
        self.assertIn("ghcr.io/juniper/nita-robot:latest", workflow)
        self.assertIn("ubuntu-24.04-arm", workflow)
        self.assertIn("github.repository == 'Juniper/nita'", workflow)
        self.assertIn("vars.NITA_ARM_CI_ENABLED == 'true'", workflow)

    def test_kind_ci_loads_source_built_webapp_without_registry_fallback(self):
        workflow = yaml.safe_load(NITA_CI.read_text(encoding="utf-8"))
        steps = workflow["jobs"]["e2e-kind"]["steps"]
        script = next(
            step["run"] for step in steps
            if step.get("name") == "Pull and load container images into Kind"
        )
        with tempfile.TemporaryDirectory() as directory:
            for name in ("docker", "kind"):
                executable = Path(directory) / name
                executable.write_text(f'#!/bin/sh\nprintf "{name} %s\\n" "$*"\n')
                executable.chmod(0o755)
            image = "nita-webapp-verification:local"
            env = os.environ | {
                "PATH": directory + os.pathsep + os.environ["PATH"],
                "NITA_WEBAPP_IMAGE": image,
                "NITA_JENKINS_IMAGE": "jenkins:test",
                "NITA_ANSIBLE_IMAGE": "ansible:test",
                "NITA_ROBOT_IMAGE": "robot:test",
                "CLUSTER_NAME": "test-cluster",
            }
            result = subprocess.run(
                ["bash", "-e", "-c", script],
                env=env, text=True, capture_output=True, check=True,
            )
            self.assertIn(
                f"kind load docker-image {image} --name test-cluster",
                result.stdout,
            )
            self.assertNotIn(f"docker pull {image}", result.stdout)
        checkout = next(
            step for step in steps
            if step.get("name") == "Check out companion webapp"
        )
        self.assertNotIn("if", checkout)
        self.assertEqual(
            checkout["with"]["repository"], "${{ env.WEBAPP_REPOSITORY }}"
        )
        self.assertEqual(checkout["with"]["ref"], "${{ env.WEBAPP_REF }}")
        build = next(
            step for step in steps
            if step.get("name") == "Build companion webapp test image"
        )
        self.assertNotIn("if", build)

    def test_kind_ci_validates_webapp_source_selection(self):
        workflow = yaml.safe_load(NITA_CI.read_text(encoding="utf-8"))
        steps = workflow["jobs"]["e2e-kind"]["steps"]
        script = next(
            step["run"] for step in steps
            if step.get("name") == "Validate companion source selection"
        )
        for repository, ref, expected in (
            ("example/nita-webapp", "main", 0),
            ("example/nita-webapp", "feature/proxy-auth", 0),
            ("example/nita-webapp", "v1.2.3", 0),
            ("example/nita-webapp", "a" * 40, 0),
            ("example/nita-webapp", "", 1),
            ("example/nita-webapp", "-main", 1),
            ("example/nita-webapp", "main;echo", 1),
            ("example/nita-webapp", "a..b", 1),
            ("example/nita-webapp;echo", "main", 1),
            ("nita-webapp", "main", 1),
        ):
            with self.subTest(repository=repository, ref=ref):
                result = subprocess.run(
                    ["bash", "-e", "-c", script],
                    env=os.environ | {
                        "WEBAPP_REPOSITORY": repository,
                        "WEBAPP_REF": ref,
                    },
                    text=True, capture_output=True,
                )
                self.assertEqual(result.returncode, expected)

    def test_kind_ci_records_tested_webapp_commit(self):
        workflow = yaml.safe_load(NITA_CI.read_text(encoding="utf-8"))
        steps = workflow["jobs"]["e2e-kind"]["steps"]
        names = [step.get("name") for step in steps]
        record_index = names.index("Record companion webapp commit")
        self.assertLess(names.index("Check out companion webapp"), record_index)
        self.assertLess(
            record_index, names.index("Build companion webapp test image")
        )
        script = steps[record_index]["run"]
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / ".ci-webapp"
            repo.mkdir()
            git = ["git", "-C", str(repo)]
            subprocess.run(git + ["init", "-q"], check=True)
            subprocess.run(
                git + ["-c", "user.name=t", "-c", "user.email=t@t",
                       "commit", "-q", "--allow-empty", "-m", "x"],
                check=True,
            )
            sha = subprocess.run(
                git + ["rev-parse", "HEAD"],
                text=True, capture_output=True, check=True,
            ).stdout.strip()
            summary = Path(directory) / "summary.md"
            result = subprocess.run(
                ["bash", "-e", "-c", script],
                cwd=directory,
                env=os.environ | {
                    "WEBAPP_REPOSITORY": "example/nita-webapp",
                    "WEBAPP_REF": "main",
                    "GITHUB_STEP_SUMMARY": str(summary),
                },
                text=True, capture_output=True, check=True,
            )
            self.assertIn(f"example/nita-webapp@{sha}", result.stdout)
            self.assertIn(f"example/nita-webapp@{sha}", summary.read_text())

    def test_kind_ci_installs_third_party_imports_of_its_pytest_modules(self):
        if not hasattr(sys, "stdlib_module_names"):
            self.skipTest("requires Python 3.10+")
        steps = yaml.safe_load(NITA_CI.read_text(encoding="utf-8"))[
            "jobs"]["e2e-kind"]["steps"]
        install = next(
            step["run"] for step in steps
            if step.get("name") == "Install integration-test dependencies"
        )
        installed = set()
        for requirements in re.findall(r"-r\s+(\S+)", install):
            for line in (ROOT / requirements).read_text().splitlines():
                name = re.match(r"[A-Za-z0-9_.-]*", line.strip()).group()
                if name:
                    installed.add(name.lower().replace("_", "-"))
        test_files = set()
        for step in steps:
            run = step.get("run", "")
            if not re.search(r"^\s*pytest\b", run, re.M):
                continue
            test_files.update(
                ROOT / path for path in re.findall(r"tests/[\w/]+\.py", run)
            )
            config = re.search(r"pytest -c (\S+\.ini)", run)
            if config:
                parser = configparser.ConfigParser()
                parser.read(ROOT / config.group(1))
                for testpath in parser["pytest"]["testpaths"].split():
                    test_files.update((ROOT / testpath).glob("*.py"))
        self.assertIn(ROOT / "tests" / "test_software_inventory.py", test_files)
        # urllib3 is installed as a dependency of requests.
        distributions = {"yaml": "pyyaml", "urllib3": "requests"}
        missing = set()
        for path in test_files:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    modules = [node.module]
                else:
                    continue
                for module in modules:
                    top = module.split(".")[0]
                    local = (ROOT / top).is_dir() or any(
                        (ROOT / directory / f"{top}.py").exists()
                        for directory in ("tests", "tools")
                    )
                    if top in sys.stdlib_module_names or local:
                        continue
                    if distributions.get(top, top) not in installed:
                        missing.add(f"{path.relative_to(ROOT)}: {top}")
        self.assertEqual(sorted(missing), [])

    def test_junos_mcp_publisher_is_multiarch_and_upstream_only(self):
        workflow = JUNOS_MCP_CI.read_text(encoding="utf-8")
        self.assertIn("linux/amd64", workflow)
        self.assertIn("linux/arm64", workflow)
        self.assertIn("github.repository == 'Juniper/nita'", workflow)
        self.assertIn(
            'immutable_tag="source-${SOURCE_SHA:0:12}-run-${GITHUB_RUN_ID}"',
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
