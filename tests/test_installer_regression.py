import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = ROOT / "install.sh"
APPLY_K8S_SH = ROOT / "k8s" / "apply-k8s.sh"


class InstallerRegressionTests(unittest.TestCase):
    def setUp(self):
        self.install_text = INSTALL_SH.read_text(encoding="utf-8")
        self.apply_text = APPLY_K8S_SH.read_text(encoding="utf-8")

    def test_ubuntu_installs_supported_openjdk_package(self):
        self.assertIn("openjdk-21-jre-headless", self.install_text)
        self.assertNotIn("openjdk-19-jre-headless", self.install_text)

    def test_jdk_19_java_home_is_not_global_default(self):
        self.assertNotRegex(
            self.install_text,
            r"^JAVA_HOME=\$\{JAVA_HOME:=\$NITAROOT/jdk-19\.0\.1\}",
            msg="AlmaLinux tarball JAVA_HOME must not be the global default",
        )

    def test_core_configmaps_are_created_before_core_apply(self):
        apply_pos = self.install_text.index("bash apply-k8s.sh")
        for name in (
            "proxy-config-cm",
            "proxy-cert-cm",
            "jenkins-crt",
            "jenkins-keystore",
        ):
            create_pos = self.install_text.index(f"kubectl create cm {name}")
            self.assertLess(
                create_pos,
                apply_pos,
                msg=f"{name} must exist before deployments are applied",
            )

    def test_core_apply_excludes_optional_junos_mcp_manifests(self):
        files_match = re.search(r'^FILES="([^"]+)"', self.apply_text, re.MULTILINE)
        self.assertIsNotNone(files_match, "apply-k8s.sh should define FILES")
        files = files_match.group(1).split()
        self.assertNotIn("junos-mcp-deployment.yaml", files)
        self.assertNotIn("junos-mcp-service.yaml", files)

    def test_core_apply_preflights_required_configmaps(self):
        for name in (
            "proxy-config-cm",
            "proxy-cert-cm",
            "jenkins-crt",
            "jenkins-keystore",
        ):
            self.assertIn(name, self.apply_text)
        self.assertRegex(self.apply_text, r"kubectl get cm .*\$\{cm\}")


if __name__ == "__main__":
    unittest.main()
