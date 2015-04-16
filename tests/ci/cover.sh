#!/bin/bash -e
#
# Copyright 2015: Mirantis Inc.
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


# Checkout to master to collect base line coverage
git stash
git checkout master

python setup.py testr --coverage --testr-args=$@
baseline=`coverage report | tail -1 | tr " " "\n" | tail -1`

# Checkout back to user directory to get current coverage
git checkout -
git stash pop || true

python setup.py testr --coverage --testr-args=$@
current=`coverage report | tail -1 | tr " " "\n" | tail -1 `

echo "Coverage baseline: ${baseline} current: ${current}"

# If coverage was reduced by 0.01% job will fail

code=`python -c "base=float(\"${baseline}\"[:-1]); current=float(\"${current}\"[:-1]); print(base - current > 0.01 and 1 or 0)"`


if [ $code -eq 0 ];
then
    echo "Thank you! You are awesome! Keep writing unit tests! :)"
else
    echo "Please write more unit tests, we should keep our test coverage :( "
fi

exit $code
