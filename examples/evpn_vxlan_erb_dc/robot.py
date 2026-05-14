#!/usr/bin/python3
import yaml
import os
import sys

# insist on the user providing the name of the job
if len(sys.argv) < 2:
    print("Must provide job name as the first argument")
    sys.exit(1)
job_ansible = sys.argv[1]

# Accept two calling conventions:
#   robot.py job_ansible job_robot                              (images from env vars)
#   robot.py job_ansible ansible_image job_robot robot_image   (explicit images)
if len(sys.argv) == 3:
    image_name = os.environ.get('NITA_ANSIBLE_IMAGE', 'ghcr.io/juniper/nita-ansible:latest')
    job_robot = sys.argv[2]
    robot_image = os.environ.get('NITA_ROBOT_IMAGE', 'ghcr.io/juniper/nita-robot:latest')
elif len(sys.argv) == 5:
    image_name = sys.argv[2]
    job_robot = sys.argv[3]
    robot_image = sys.argv[4]
else:
    print("Usage: robot.py job_ansible job_robot")
    print("       robot.py job_ansible ansible_image job_robot robot_image")
    sys.exit(1)

# get path that is to be used inside the job for the working directory
path = os.getcwd()

job_1 = f"""apiVersion: batch/v1
kind: Job
metadata:
  name: {job_ansible}
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
        args: ["-c", "bash test_setup.sh", "/tmp"]
        volumeMounts:
        - name: default
          mountPath: /project/
      volumes:
      - name: default
        hostPath:
          path: /var/nita_project
      restartPolicy: Never"""

with open(f'{job_ansible}.yaml', 'w') as file:
    print(job_1, file=file)
    
job_2 = f"""apiVersion: batch/v1
kind: Job
metadata:
  name: {job_robot}
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 120
  template:
    spec:
      serviceAccountName: internal-jenknis-pod
      containers:
      - name: nita-robot
        image: {robot_image}
        workingDir: {path}/test
        command: ["/bin/bash"]
        args: ["-c", "robot -C ansi -L TRACE {path}/test/tests"]
        env:
        - name: ROBOT_OPTIONS
          value: "-d {path}/test/outputs"
        volumeMounts:
        - name: default
          mountPath: /project/
      volumes:
      - name: default
        hostPath:
          path: /var/nita_project
      restartPolicy: Never"""
      
with open(f'{job_robot}.yaml', 'w') as file:
    print(job_2, file=file)      