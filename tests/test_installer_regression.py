import re
import subprocess
import tempfile
import unittest
from pathlib import Path


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

    def test_fork_ci_uses_canonical_images_and_gates_upstream_arm_runner(self):
        workflow = NITA_CI.read_text(encoding="utf-8")
        self.assertNotIn("github.repository_owner", workflow)
        self.assertIn("ghcr.io/juniper/nita-webapp:latest", workflow)
        self.assertIn("ghcr.io/juniper/nita-jenkins:latest", workflow)
        self.assertIn("ghcr.io/juniper/nita-ansible:latest", workflow)
        self.assertIn("ghcr.io/juniper/nita-robot:latest", workflow)
        self.assertIn("ubuntu-24.04-arm", workflow)
        self.assertIn("github.repository == 'Juniper/nita'", workflow)
        self.assertIn("vars.NITA_ARM_CI_ENABLED == 'true'", workflow)

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
