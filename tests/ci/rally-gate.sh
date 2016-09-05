#!/bin/bash -ex
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This script is executed by post_test_hook function in devstack gate.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $SCRIPT_DIR/rally_gate_functions.sh

PROJECT=`echo $ZUUL_PROJECT | cut -d \/ -f 2`

RALLY_JOB_DIR=$BASE/new/$PROJECT/rally-scenarios
if [ ! -d $RALLY_JOB_DIR ]; then
    RALLY_JOB_DIR=$BASE/new/$PROJECT/rally-jobs
fi

echo $RALLY_JOB_DIR
echo $RALLY_DIR
ls $BASE/new/$PROJECT

setUp $RALLY_JOB_DIR

BASE_FOR_TASK=${RALLY_JOB_DIR}/${RALLY_SCENARIO}

TASK=${BASE_FOR_TASK}.yaml
TASK_ARGS=""
if [ -f ${BASE_FOR_TASK}_args.yaml ]; then
    TASK_ARGS="--task-args-file ${BASE_FOR_TASK}_args.yaml"
fi

run $TASK $TASK_ARGS
