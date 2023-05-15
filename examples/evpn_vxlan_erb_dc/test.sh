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

umask 0002

# Creating of result files and making them R/W by everybody
mkdir -p test/outputs
mkdir -p test/resource_files/tmp
touch test/outputs/output.xml
touch test/outputs/log.html
touch test/outputs/report.html

export PYTHONPATH=libraries

(cd test && robot -C ansi -L TRACE tests/)

chmod -R 777 test/tests
chmod -R 777 test/resource_files/tmp
chmod -R 777 test/outputs

