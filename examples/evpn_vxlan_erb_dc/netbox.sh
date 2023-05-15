#!/bin/bash
# ********************************************************
#
# Project: nita-webapp
#
# Copyright (c) Juniper Networks, Inc., 2021. All rights reserved.
#
# Notice and Disclaimer: This code is licensed to you under the Apache 2.0 License (the "License"). You may not use this code except in compliance with the License. This code is not an official Juniper product. You can obtain a copy of the License at https://www.apache.org/licenses/LICENSE-2.0.html
#
# SPDX-License-Identifier: Apache-2.0
#
# Third-Party Code: This code may depend on other components under separate copyright notice and license terms. Your use of the source code for those components is subject to the terms and conditions of the respective license as noted in the Third-Party source code file.
#
# ********************************************************

rm -f ~/.ssh/known_hosts
temp_dir=$1
build_dir=/var/tmp/build

if [ $# -ne 0 ] && [ "$temp_dir" !=  "None" ]; then
        build_dir=$temp_dir
fi

ansible-playbook -i hosts netbox/sites.yaml  --extra-vars "build_dir=$build_dir"
touch $build_dir/ansible-run.log
sudo chmod 664 $build_dir/ansible-run.log
