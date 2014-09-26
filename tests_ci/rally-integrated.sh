#!/bin/sh -ex

env

mkdir -p .testrepository
python -m subunit.run discover tests_functional > .testrepository/subunit.log
EXIT_CODE=$?

subunit2pyunit < .testrepository/subunit.log
subunit-stats < .testrepository/subunit.log

exit $EXIT_CODE
