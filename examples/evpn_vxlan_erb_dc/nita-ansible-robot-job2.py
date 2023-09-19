import yaml
import os
path = os.getcwd()
with open('nita-ansible-robot-job2.yaml', 'r') as file:
    data = yaml.load(file, Loader=yaml.FullLoader)
    data['spec']['template']['spec']['containers'][0]['workingDir'] = path+"/test"
    data['spec']['template']['spec']['containers'][0]['args'][1] = "robot -C ansi -L TRACE "+path+"/test/tests"
    data['spec']['template']['spec']['containers'][0]['env'][0]['value'] = "-d "+path+"/test/outputs"
    with open('nita-ansible-robot-job2.yaml', 'w') as file:
        yaml.dump(data, file)
