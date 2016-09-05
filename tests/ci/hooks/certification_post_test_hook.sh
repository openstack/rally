#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $SCRIPT_DIR/../rally_gate_functions.sh

setUp

TASK=$RALLY_DIR/certification/openstack/task.yaml
TASK_ARGS=$RALLY_DIR/rally-jobs/certifcation_task_args.yaml

TASK_ARGS="--task-args-file $TASK_ARGS"

run $TASK $TASK_ARGS
