#!/usr/bin/python3
import yaml
import os
import sys

# insist on the user providing the name of the job
if len(sys.argv) < 2:
    print("Must provide job name as the first argument")
    sys.exit(1)
job_ansible = sys.argv[1]

# insist on the user providing the image name as the second argument
if len(sys.argv) < 3:
    print("Must provide image name as the second argument")
    sys.exit(1)
image_name = sys.argv[2]

if len(sys.argv) < 4:
    print("Must provide job-robot name")
    sys.exit(1)
job_robot = sys.argv[3]

if len (sys.argv) < 5:
    print("Must provide ROBOT image name")
    sys.exit(1)
robot_image = sys.argv[4]    

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