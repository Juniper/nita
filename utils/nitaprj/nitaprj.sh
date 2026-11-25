#!/bin/bash

SCRIPT_VERSION=1.1
script_name=$(basename "$0")
PROFILE_DIR=./profiles
INNER_SCRIPT_NAME="nitaprj"
DEPLOYMENT_DIR=./deploy
ZIP=`which zip`
WGET=`which wget`
CURL=`which curl`
YAML2XLS=`which yaml2xls.py`
NITA_YAML_TO_EXCEL_URL="https://github.com/Juniper/nita-yaml-to-excel/archive/refs/heads/main.zip"
#TARGET_FILE=${NITA_YAML_TO_EXCEL_URL##*/}
TARGET_FILE=nita-yaml-to-excel.zip
project_name=""
TMPDIR=${TMPDIR:-/tmp}
PIPUNZIPDIR=${TMPDIR}/pip-unzip

abs_path() {
    case "$1" in
        /*)
            echo "$1"
            ;;
        *)
            if [ -e "$1" ]; then
                local path_dir
                local path_base
                path_dir=$(dirname "$1")
                path_base=$(basename "$1")
                echo "$(cd "$path_dir" && pwd -P)/$path_base"
            else
                echo "$1"
            fi
            ;;
    esac
}

append_line_once() {
    local target_file=$1
    local target_line=$2
    grep -Fxq "$target_line" "$target_file" && return
    if [ -s "$target_file" ] && [ "$(tail -c 1 "$target_file" | od -An -t x1 | tr -d ' ')" != "0a" ]; then
        echo >> "$target_file"
    fi
    echo "$target_line" >> "$target_file"
}

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

fetch_file() {
    url=$1
    dest=$2
    if [ -z "$WGET" ] ; then
        if [ -z "$CURL" ] ; then
            echo "Error: Neither wget nor curl command found. Please install wget or curl utility."
            exit 1
        else
            $CURL -L -o $dest $url
            return
        fi    
    fi
    $WGET -O $dest $url
}

verify_zip_wget() {
    if [ -z "$ZIP" ] ; then
        echo "Error: zip command not found. Please install zip utility."
        exit 1
    fi
    if [ -z "$WGET" ] && [ -z "CURL" ] ; then
        echo "Error: wget or curl commands not found. Please install wget or curl utility."
        exit 1
    fi
}
usage() {
    if [ ${script_name} == ${INNER_SCRIPT_NAME} ]; then
        usage_inner
    fi
    echo "Usage: $0 <command> [options]"    
    echo "Commands:"
    echo "  create <projectname> [profilename] Create a new project (default profile: jtaf-ansible)"
    echo "  generate-role <projectname> -p <yang-paths-and-files> -x <xml-config-files> -t <device-type> [-v <yang-version>]"
    echo "  build <projectname>  Build the project" 
    echo "  version" 
    exit 1
}

usage_inner() {
    echo "Usage: $0 <command> [options]"    
    echo "Commands:"
    echo "  generate-role -p <yang-paths-and-files> -x <xml-config-files> -t <device-type> [-v <yang-version>]"
    echo "  build  Build the project" 
    echo "  version" 
    exit 1
}

usage_generate_role() {
    if [ ${script_name} == ${INNER_SCRIPT_NAME} ]; then
        echo "Usage: $0 generate-role -p <yang-paths-and-files> -x <xml-config-files> -t <device-type> [-v <yang-version>]"
    else
        echo "Usage: $0 generate-role <projectname> -p <yang-paths-and-files> -x <xml-config-files> -t <device-type> [-v <yang-version>]"
    fi
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
    profile_name=${2:-jtaf-ansible}
    echo "Creating project '$project_name' using profile '$profile_name'"
    mkdir $project_name
    cp -r $PROFILE_DIR/${profile_name}/* $project_name
    if [ "$profile_name" = "jtaf-ansible" ]; then
        cp "$(dirname "$0")/enrich_variables.py" "$project_name/enrich_variables.py" || exit 1
    fi
    if [ -f ${project_name}/project.yaml ]; then
        sed -i.bak "s/__PROJECT_NAME__/${project_name}/g" ${project_name}/project.yaml
        rm -f ${project_name}/project.yaml.bak
    fi
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
            fetch_file $NITA_YAML_TO_EXCEL_URL $TARGET_FILE
            unzip -d ${PIPUNZIPDIR} ${TARGET_FILE}
            pip3 install ${PIPUNZIPDIR}/nita-yaml-to-excel-main/
            rm -rf ${PIPUNZIPDIR}
            rm -f $TARGET_FILE
            YAML2XLS=`which yaml2xls.py`
        else
            echo "User refused to install yaml2xls.py. Stopping"
            exit 1	
        fi	     
   fi	   
}

check_jtaf() {
   if which jtaf-yang2ansible 1>/dev/null 2>&1 ; then
      :
   else
      echo "Error: jtaf-yang2ansible command not found. Please install junos-terraform or add it to PATH."
      exit 1
   fi
    if which jtaf-xml2yaml 1>/dev/null 2>&1 ; then
        :
    else
        echo "Error: jtaf-xml2yaml command not found. Please install junos-terraform or add it to PATH."
        exit 1
    fi
}

add_role_to_sites() {
    local sites_file=$1
    local role_name=$2
    local role_vars='  vars:
    tmp_dir: "configs"
    jtaf_vars_root: "{{ playbook_dir }}/.."'

    if [ -f "$(dirname "$sites_file")/runtime.yaml" ]; then
        role_vars='  vars_files:
    - runtime.yaml'
    fi

    if grep -q "role: ${role_name}" "$sites_file" ; then
        return
    fi

    cat >> "$sites_file" <<EOF

- name: Apply JTAF role ${role_name}
  hosts: all
  connection: local
  gather_facts: no
${role_vars}
  roles:
    - role: ${role_name}
      delegate_to: localhost
EOF
}

action_generate_role() {
    project_name=$1
    shift

    local project_dir
    if [ ${script_name} == ${INNER_SCRIPT_NAME} ]; then
        project_dir=$(pwd)
    else
        if [ -z "$project_name" ] || [ ! -d "$project_name" ]; then
            echo "Error: Directory '$project_name' does not exist."
            exit 1
        fi
        project_dir=$(abs_path "$project_name")
    fi

    local generator_args=()
    local xml_args=()
    local has_yang=false
    local has_xml=false
    local device_type=""
    local yang_version=""

    while [ $# -gt 0 ]; do
        case "$1" in
            -p)
                generator_args+=("-p")
                shift
                if [ $# -eq 0 ] || [[ "$1" == -* ]]; then
                    usage_generate_role
                fi
                while [ $# -gt 0 ] && [[ "$1" != -* ]]; do
                    generator_args+=("$(abs_path "$1")")
                    has_yang=true
                    shift
                done
                ;;
            -x)
                generator_args+=("-x")
                shift
                if [ $# -eq 0 ] || [[ "$1" == -* ]]; then
                    usage_generate_role
                fi
                while [ $# -gt 0 ] && [[ "$1" != -* ]]; do
                    local xml_file
                    xml_file=$(abs_path "$1")
                    generator_args+=("$xml_file")
                    xml_args+=("$xml_file")
                    has_xml=true
                    shift
                done
                ;;
            -t)
                shift
                if [ $# -eq 0 ] || [[ "$1" == -* ]]; then
                    usage_generate_role
                fi
                device_type=$1
                generator_args+=("-t" "$device_type")
                shift
                ;;
            -v)
                shift
                if [ $# -eq 0 ] || [[ "$1" == -* ]]; then
                    usage_generate_role
                fi
                yang_version=$1
                shift
                ;;
            *)
                usage_generate_role
                ;;
        esac
    done

    if [ "$has_yang" != true ] || [ "$has_xml" != true ] || [ -z "$device_type" ]; then
        usage_generate_role
    fi

    if [[ "$device_type" == */* ]] || [[ "$device_type" == *..* ]]; then
        echo "Error: Device type must not contain '/' or '..'."
        exit 1
    fi

    check_jtaf

    local work_dir
    work_dir=$(mktemp -d "${TMPDIR}/nitaprj-jtaf.XXXXXX") || exit 1
    local generated_dir="${work_dir}/ansible-provider-junos-${device_type}"
    local role_name="${device_type}_role"

    echo "Generating JTAF Ansible role '${role_name}'"
    if [ -n "$yang_version" ]; then
        echo "YANG version: ${yang_version}"
    fi

    ( cd "$work_dir" && jtaf-yang2ansible "${generator_args[@]}" )
    local generate_status=$?
    if [ $generate_status -ne 0 ]; then
        rm -rf "$work_dir"
        exit $generate_status
    fi

    if [ ! -d "${generated_dir}/roles/${role_name}" ]; then
        echo "Error: Expected generated role '${generated_dir}/roles/${role_name}' was not created."
        rm -rf "$work_dir"
        exit 1
    fi

    mkdir -p "${project_dir}/roles" "${project_dir}/filter_plugins" "${project_dir}/configs" "${project_dir}/build"
    rm -rf "${project_dir}/roles/${role_name}"
    cp -R "${generated_dir}/roles/${role_name}" "${project_dir}/roles/${role_name}"
    cp -R "${generated_dir}/filter_plugins/." "${project_dir}/filter_plugins/"

    if [ -f "${generated_dir}/trimmed_schema.json" ]; then
        cp "${generated_dir}/trimmed_schema.json" "${project_dir}/configs/trimmed_schema.json"
        jtaf-xml2yaml \
            -j "${generated_dir}/trimmed_schema.json" \
            -x "${xml_args[@]}" \
            -d "${project_dir}" \
            --hosts-file "${project_dir}/hosts" \
            --host-vars-dir "${project_dir}/host_vars" \
            --group-vars-dir "${project_dir}/group_vars"
        local xml2yaml_status=$?
        if [ $xml2yaml_status -ne 0 ]; then
            rm -rf "$work_dir"
            exit $xml2yaml_status
        fi
        if [ -f "${project_dir}/build/runtime.yaml" ]; then
            cp "$(dirname "$(readlink -f "$0")")/enrich_variables.py" "${project_dir}/enrich_variables.py" || exit 1
            python3 "${project_dir}/enrich_variables.py" "$project_dir" \
                --record-empty-leaves "${xml_args[@]}"
            local record_status=$?
            if [ $record_status -ne 0 ]; then
                rm -rf "$work_dir"
                exit $record_status
            fi
            append_line_once "${project_dir}/manifest" "enrich_variables.py"
        fi
    fi

    touch "${project_dir}/manifest" "${project_dir}/build/sites.yaml"
    add_role_to_sites "${project_dir}/build/sites.yaml" "$role_name"
    append_line_once "${project_dir}/manifest" "roles/${role_name}"
    append_line_once "${project_dir}/manifest" "filter_plugins"
    append_line_once "${project_dir}/manifest" "configs"
    append_line_once "${project_dir}/manifest" "group_vars"
    append_line_once "${project_dir}/manifest" "host_vars"
    append_line_once "${project_dir}/manifest" "hosts"

    rm -rf "$work_dir"
    echo "Generated role '${role_name}' in ${project_dir}/roles/${role_name}"
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
	 mv  ${xls_file} ${xls_file}.bak
    fi	    
    $ZIP -r ${target_archive} -x "group_vars/env.y*" "*/__pycache__/*" "*.pyc" -@ < manifest

    # workaround to make sure env variables are replaced with "XXXXXXXXX"
    # to prevent accidental credential leak
    # backup env.yaml to tmp 
    NITATMP=${TMPDIR}/nitaprj.tmp
    rm -rf $NITATMP
    mkdir $NITATMP
    cp group_vars/env.y* $NITATMP/
    # replace existing env.yaml with scrubbed version
    for f in $NITATMP/env.y* ; do
     f_base=`basename $f`
     cat $f | sed -E 's/^( .+\:).+/\1 XXXXXXX/' > group_vars/${f_base}
    done	    

    yaml_files=$(find group_vars host_vars -type f \( -name "*.yaml" -o -name "*.yml" \) ! -name "registry.yaml" | sort)
    if [ -z "$yaml_files" ]; then
        echo "Error: No YAML variable files found under group_vars or host_vars."
        cp $NITATMP/env.y* group_vars
        rm -rf  $NITATMP
        exit 1
    fi

    $YAML2XLS $yaml_files ${project_name}.xlsx

    #return original env.yaml
    cp $NITATMP/env.y* group_vars
    rm -rf  $NITATMP
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
if [ $1 != 'version' ] && [ ${script_name} != ${INNER_SCRIPT_NAME} ] && [ -z "$2" ]; then
    usage
fi

verify_zip_wget

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
    generate-role)
        if [ ${script_name} == ${INNER_SCRIPT_NAME} ]; then
            project_name=$(basename $(pwd))
            action_generate_role $project_name "${@:2}"
        else
            project_name=$2
            action_generate_role $project_name "${@:3}"
        fi
        ;;
    version)
        echo "$SCRIPT_VERSION"	    
        ;;	    
    *)
        usage
        ;;
esac


