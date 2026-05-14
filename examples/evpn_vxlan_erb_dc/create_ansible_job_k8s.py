#!/usr/bin/python3
import yaml
import os
import sys

# insist on the user providing the name of the job
if len(sys.argv) < 2:
    print("Must provide job name as the first argument")
    sys.exit(1)
job_name = sys.argv[1]

# use image from argument, NITA_ANSIBLE_IMAGE env var, or built-in default
if len(sys.argv) >= 3:
    image_name = sys.argv[2]
else:
    image_name = os.environ.get('NITA_ANSIBLE_IMAGE', 'ghcr.io/juniper/nita-ansible:latest')

# get path that is to be used inside the job for the working directory
path = os.getcwd()

# yaml file to be used as the starting point for creating a new job
job_yaml = f"""
apiVersion: batch/v1
kind: Job
metadata:
  name: {job_name}
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 120
  template:
    spec:
      serviceAccountName: internal-jenknis-pod
      containers:
      - name: nita-ansible
        image: {image_name}
        workingDir: {path}
        command: ["/bin/bash"]
        args: ["-c", "bash {job_name}.sh", "/tmp"]
        volumeMounts:
        - name: default
          mountPath: /project/
      volumes:
      - name: default
        hostPath:
          type: DirectoryOrCreate
          path: /var/nita_project
      restartPolicy: Never
"""

with open(f'{job_name}.yaml', 'w') as file:
    print(job_yaml, file=file)
