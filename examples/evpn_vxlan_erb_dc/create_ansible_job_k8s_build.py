import yaml
import os
path = os.getcwd()
with open('nita-ansible-job-build.yaml', 'r') as file:
    data = yaml.load(file, Loader=yaml.FullLoader)
    data['spec']['template']['spec']['containers'][0]['workingDir'] = path
    with open('nita-ansible-job-build.yaml', 'w') as file:
        yaml.dump(data, file)
