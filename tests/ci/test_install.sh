#!/bin/sh -ex
#
# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

env

sudo yum remove -y python-crypto || true

# NOTE(pabelanger): We run apt-get update to ensure we don't have a stale
# package cache in the gate.
sudo apt-get update || true

sudo ./install_rally.sh --system --yes
rally deployment list
[ -d /etc/bash_completion.d ] && cat /etc/bash_completion.d/rally.bash_completion || true

sudo ./install_rally.sh --system --yes
rally deployment list

sudo ./install_rally.sh --yes -d /tmp/rallytest_root/
/tmp/rallytest_root/bin/rally deployment list
cat /tmp/rallytest_root/etc/bash_completion.d/rally.bash_completion

sudo rm -fr ~/.rally

./install_rally.sh --yes -d /tmp/rallytest_user
/tmp/rallytest_user/bin/rally deployment list

./install_rally.sh --overwrite --dbtype sqlite
