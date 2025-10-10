#!/usr/bin/python3
import yaml
import os
import sys

# insist on the user providing the name of the job
if len(sys.argv) < 2:
    print("Must provide job name as the first argument")
    sys.exit(1)
job_name = sys.argv[1]

# insist on the user providing the image name as the second argument
if len(sys.argv) < 3:
    print("Must provide image name as the second argument")
    sys.exit(1)
image_name = sys.argv[2]

# get path that is to be used inside the job for the working directory
path = os.getcwd()

def get_environment_from_yaml(env_file):
    env = {}
    if os.path.exists(env_file):      
      with open(env_file, 'r') as file:
          try:
              env = yaml.safe_load(file)
          except yaml.YAMLError as exc:
              print(exc)
      return env
    
    
env_file='group_vars/env.yaml'
env=get_environment_from_yaml(env_file)
k8s_env="        env:\n"
for k,v in env['env'].items():
    k8s_env+=f"          - name: {k}\n            value: \"{v}\"\n"

k8s_env.rstrip('\n')     
# yaml file to be used as the starting point for creating a new job
job_yaml1 = f"""
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
"""
job_yaml2= """ 
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
job_yaml=job_yaml1+k8s_env+job_yaml2 

with open(f'{job_name}.yaml', 'w') as file:
    print(job_yaml, file=file)
