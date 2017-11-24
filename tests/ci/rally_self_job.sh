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
if [ -n "$ZUUL_PROJECT" ]; then
    HTML_REPORT=testr_results.html
    JSON_REPORT=testr_results.json
else
    HTML_REPORT=rally_self_results.html
    JSON_REPORT=rally_self_results.json
fi
RND=$(head /dev/urandom | tr -dc a-z0-9 | head -c 5)
TMP_RALLY_CONF="/tmp/self-rally-$RND.conf"
TMP_RALLY_DB="/tmp/self-rally-$RND.sqlite"
DBCONNSTRING="sqlite:///$TMP_RALLY_DB"
RALLY="rally --config-file $TMP_RALLY_CONF"

# Create temp db
cp etc/rally/rally.conf.sample $TMP_RALLY_CONF
sed -i.bak "s|#connection =.*|connection = \"$DBCONNSTRING\"|" $TMP_RALLY_CONF
rally --config-file $TMP_RALLY_CONF db create

# Create self deployment
$RALLY -d deployment create --name=self

# Run task
$RALLY -d --plugin-paths=$PLUGIN_PATHS task start $TASK_FILE
$RALLY task report --html-static --out $HTML_REPORT
$RALLY task report --json --out $JSON_REPORT

if [ -n "$ZUUL_PROJECT" ]; then
    gzip -9 -f $HTML_REPORT
    gzip -9 -f $JSON_REPORT
fi

# Check sla (this may fail the job)
$RALLY task sla-check
