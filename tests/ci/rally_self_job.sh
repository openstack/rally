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

TASK_FILE=$1
PLUGIN_PATHS=rally-jobs/plugins

mkdir -p .test_results
HTML_REPORT=.test_results/self_report.html
JSON_REPORT=.test_results/self_report.json

RND=$(head /dev/urandom | tr -dc a-z0-9 | head -c 5)
TMP_RALLY_CONF="/tmp/self-rally-$RND.conf"
TMP_RALLY_DB="/tmp/self-rally-$RND.sqlite"
DBCONNSTRING="sqlite:///$TMP_RALLY_DB"
RALLY="rally --config-file $TMP_RALLY_CONF"

# Create temp cfg
cp etc/rally/rally.conf.sample $TMP_RALLY_CONF
sed -i.bak "s|#connection =.*|connection = \"$DBCONNSTRING\"|" $TMP_RALLY_CONF

# ensure plugins loading
$RALLY --debug --plugin-paths=$PLUGIN_PATHS plugin show --name FakePlugin.testplugin

# Create db
$RALLY db create

# Create self deployment
$RALLY -d env create --name=self

# Run task
set +e
$RALLY -d --plugin-paths=$PLUGIN_PATHS task start $TASK_FILE
if [ $? -eq 1 ]; then
    exit 1
fi
set -e

$RALLY task report --html-static --out $HTML_REPORT
$RALLY task report --json --out $JSON_REPORT

# Check sla (this may fail the job)
$RALLY task sla-check
