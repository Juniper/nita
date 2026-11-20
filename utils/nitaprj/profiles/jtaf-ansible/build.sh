#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
temp_dir=${1:-None}
build_dir=/var/tmp/build

if [ $# -ne 0 ] && [ "$temp_dir" != "None" ]; then
    build_dir=$temp_dir
fi

mkdir -p "$build_dir/log"
touch "$build_dir/ansible-run.log"
chmod 664 "$build_dir/ansible-run.log"

if ! ansible-playbook -i hosts build/commit.yaml --syntax-check \
    --extra-vars "build_dir=$build_dir" | tee -a "$build_dir/ansible-run.log"; then
    echo "Deployment validation failed. In Jenkins, use bash ./run_build.sh to run in the NITA Ansible image." >&2
    exit 1
fi

ansible-playbook -i hosts build/sites.yaml --extra-vars "build_dir=$build_dir" \
    | tee -a "$build_dir/ansible-run.log"
ansible-playbook -i hosts build/commit.yaml --extra-vars "build_dir=$build_dir" \
    | tee -a "$build_dir/ansible-run.log"