#!/bin/sh -ex
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

# This script is executed by post_test_hook function in desvstack gate.

PROJECT=`echo $ZUUL_PROJECT | cut -d \/ -f 2`
SCENARIO=$BASE/new/$PROJECT/rally-scenarios/${RALLY_SCENARIO}.yaml
PLUGINS_DIR=$BASE/new/$PROJECT/rally-scenarios/plugins

if [ -d $PLUGINS_DIR ]; then
 mkdir -p ~/.rally/plugins/scenarios
 cp $PLUGINS_DIR/*.py ~/.rally/plugins/scenarios/
fi

rally use deployment --name devstack
rally -v task start --task $SCENARIO
mkdir rally-plot
rally task plot2html --out rally-plot/results.html
gzip -9 rally-plot/results.html
env
