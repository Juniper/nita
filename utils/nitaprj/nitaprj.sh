#!/bin/bash

SCRIPT_VERION=1.0
script_name=$(basename "$0")
PROFILE_DIR=./profiles
INNER_SCRIPT_NAME="nitaprj"
DEPLOYMENT_DIR=./deploy
ZIP=`which zip`
WGET=`which wget`
YAML2XLS=`which yaml2xls.py`
project_name=""

get_project_name() {
   project_name=$1
    if [ ${script_name} != ${INNER_SCRIPT_NAME} ]; then
        if [ -d "$project_name" ]; then
            cd $project_name
        else
            echo "Error: Directory '$project_name' does not exist."
            exit 1
        fi
    else
       project_name=$(basename $(pwd))
    fi
}

usage() {
    if [ ${script_name} == ${INNER_SCRIPT_NAME} ]; then
        usage_inner
    fi
    echo "Usage: $0 <command> [options]"    
    echo "Commands:"
    echo "  create <projectname> [profilename] Create a new project"
    echo "  build <projectname>  Build the project" 
    echo "  version" 
    exit 1
}

usage_inner() {
    echo "Usage: $0 <command> [options]"    
    echo "Commands:"
    echo "  build  Build the project" 
    echo "  version" 
    exit 1
}

ask() {
    echo -n "$1 [y/n]: "
    read answer
    case $answer in
        Y|y)
            return 0
            ;;
        N|n)
            return 1
            ;;
        *)
            ask "$1"
            ;;
    esac
}

action_create() {
    project_name=$1
    if [ -d "$project_name" ]; then
        echo "Error: Directory '$project_name' already exists."
        exit 1
    fi      
    profile_name=${2:-generic}
    echo "Creating project '$project_name' using profile '$profile_name'"
    mkdir $project_name
    cp -r $PROFILE_DIR/${profile_name}/* $project_name
    ln -s ../${script_name} ${project_name}/${INNER_SCRIPT_NAME} 
    ask "Do you want to create a git repository?" && git init $project_name
    echo "Empty project '$project_name' created"
    echo "You can now edit the files in '$project_name'"
    echo "You can run './nitaprj build' to build or test the project inside the project directory"
    echo "Or"
    echo "You can run './${script_name} build $project_name to build or test the project from current directory" 
}

check_yaml2xls() {
   if which yaml2xls.py 1>/dev/null 2>&1 ; then
      :
   else
     if ask "Missing yaml2xls.py. Cannot proceed without it. Do you want to install it?" ; then
#        if pip3 list | grep -q openpyxl ; then
#	   :
#        else
#            if ask "Missing openpyxl python module. Cannot proceed without it. Do you want to install it?" ; then
#		pip3 insall openpyxl
#            else
#                echo "User refused to install openpyxl python. Stopping"
#                exit 1		    
#            fi		    
#        fi	
	$WGET https://github.com/Juniper/nita-yaml-to-excel/archive/refs/heads/main.zip
	unzip main.zip
	pip3 install ./nita-yaml-to-excel/
	rm -rf ./nita-yaml-to-excel/
     else
        echo "User refused to install yaml2xls.py. Stopping"
        exit 1	
     fi	     
   fi	   
}
action_build() {
    project_name=$1
    echo "Building project '$project_name'"
    echo "Building"
    echo "Current directory is $(pwd)"
    target_archive="${project_name}.zip"
    check_yaml2xls
    xls_file=${project_name}.xlsx
    if [ -f ${target_archive} ] ; then
	 mv $target_archive ${target_archive}.bak
    fi	    
    if [ -f ${xls_file} ] ; then
	 mv  ${cls_file} ${cls_file}.bak
    fi	    
    $ZIP -r ${target_archive} -x "group_vars/env.y*" "*/__pycache__/*" "*.pyc" -@ < manifest

    # workaround to make sure env variables are replaced with "XXXXXXXXX"
    # to prevent accidental credential leak
    # backup env.yaml to tmp 
    rm -rf /tmp/nitaprj.tmp
    mkdir /tmp/nitaprj.tmp
    cp group_vars/env.y* /tmp/nitaprj.tmp
    # replace existing env.yaml with scrubbed version
    for f in /tmp/nitaprj.tmp/env.y* ; do
     f_base=`basename $f`
     cat $f | sed -E 's/^( .+\:).+/\1 XXXXXXX/' > group_vars/${f_base}
    done	    

    $YAML2XLS group_vars/* host_vars/* ${project_name}.xlsx

    #return original env.yaml
    cp /tmp/nitaprj.tmp/env.y* group_vars
    rm -rf  /tmp/nitaprj.tmp
    echo "Build completed. Project file is $(pwd)/${target_archive}"
    echo "           Variable xlsx file is $(pwd)/${xls_file}"
    if [ ${script_name} != ${INNER_SCRIPT_NAME} ]; then
       cd .. 
    fi
}


# Check if required options are provided
if [ -z "$1" ] ; then
    usage
fi
if [ ${script_name} != ${INNER_SCRIPT_NAME} ] && [ -z "$2" ]; then
    usage
fi

case $1 in
    create)
        if [ ${script_name} == ${INNER_SCRIPT_NAME} ]; then
            echo "You can't run create command from inside the project directory"
            exit 1
        fi
        project_name=$2
        profile_name=$3
        action_create $project_name $profile_name
        ;;
    build)
        get_project_name $2
        action_build $project_name
        ;;
    version)
        echo "$SCRIPT_VERSION"	    
        ;;	    
    *)
        usage
        ;;
esac



