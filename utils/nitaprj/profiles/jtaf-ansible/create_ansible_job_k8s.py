#!/usr/bin/python3
import os
import sys

import yaml


if len(sys.argv) < 2:
    print("Must provide job name as the first argument")
    sys.exit(1)

job_name = sys.argv[1]
image_name = (
    sys.argv[2]
    if len(sys.argv) >= 3
    else os.environ.get("NITA_ANSIBLE_IMAGE", "ghcr.io/juniper/nita-ansible:latest")
)
working_dir = os.getcwd()
namespace = os.environ.get("NITA_NAMESPACE", "nita")
netconf_secret = os.environ.get("NITA_NETCONF_SECRET")

env_data = {}
if os.path.exists("group_vars/env.yaml"):
    with open("group_vars/env.yaml", "r", encoding="utf-8") as env_file:
        env_data = yaml.safe_load(env_file) or {}
else:
    print("No group_vars/env.yaml supplied; using the image's environment.")

netconf_variables = ("ANSIBLE_NET_USERNAME", "ANSIBLE_NET_PASSWORD")
job_environment = [
    {"name": name, "value": str(value)}
    for name, value in (env_data.get("env") or {}).items()
    if not netconf_secret or name not in netconf_variables
]
if netconf_secret:
    job_environment.extend(
        {
            "name": name,
            "valueFrom": {
                "secretKeyRef": {"name": netconf_secret, "key": name}
            },
        }
        for name in netconf_variables
    )

job = {
    "apiVersion": "batch/v1",
    "kind": "Job",
    "metadata": {"name": job_name, "namespace": namespace},
    "spec": {
        "backoffLimit": 0,
        "ttlSecondsAfterFinished": 120,
        "template": {
            "spec": {
                "serviceAccountName": "internal-jenknis-pod",
                "containers": [
                    {
                        "name": "nita-ansible",
                        "image": image_name,
                        "workingDir": working_dir,
                        "command": ["/bin/bash"],
                        "args": [f"{job_name}.sh", os.environ.get("build_dir", "None")],
                        "env": job_environment,
                        "volumeMounts": [
                            {"name": "default", "mountPath": "/project/"}
                        ],
                    }
                ],
                "volumes": [
                    {
                        "name": "default",
                        "hostPath": {
                            "type": "DirectoryOrCreate",
                            "path": "/var/nita_project",
                        },
                    }
                ],
                "restartPolicy": "Never",
            }
        },
    },
}

with open(f"{job_name}.yaml", "w", encoding="utf-8") as job_file:
    yaml.safe_dump(job, job_file, sort_keys=False)