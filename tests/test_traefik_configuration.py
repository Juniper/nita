import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class TraefikConfigurationTests(unittest.TestCase):
    def test_ingress_routes_are_class_scoped_and_jenkins_uses_auth(self):
        resources = list(yaml.safe_load_all((ROOT / "k8s/traefik-resources.yaml").read_text()))
        ingresses = [resource for resource in resources if resource["kind"] == "Ingress"]
        self.assertEqual(len(ingresses), 4)
        for ingress in ingresses:
            self.assertEqual(ingress["spec"]["ingressClassName"], "nita-traefik")
            annotations = ingress["metadata"]["annotations"]
            if "jenkins" in ingress["metadata"]["name"]:
                self.assertIn("jenkins-auth@file", annotations["traefik.ingress.kubernetes.io/router.middlewares"])
                self.assertIn("jenkins-identity@file", annotations["traefik.ingress.kubernetes.io/router.middlewares"])

    def test_kubernetes_and_compose_middleware_contracts_match(self):
        compose = ROOT.parent / "nita-webapp" / "traefik" / "routes.yaml"
        if not compose.exists():
            self.skipTest("companion webapp repository is unavailable")
        nita = yaml.safe_load((ROOT / "k8s/traefik/routes.yaml").read_text())
        webapp = yaml.safe_load(compose.read_text())
        self.assertEqual(nita["http"]["middlewares"], webapp["http"]["middlewares"])
        for plugin in ("bodylimit", "identityguard"):
            self.assertEqual(
                (ROOT / "k8s/traefik" / plugin / (plugin + ".go")).read_text(),
                (ROOT.parent / "nita-webapp/traefik" / plugin / (plugin + ".go")).read_text(),
            )


if __name__ == "__main__":
    unittest.main()
