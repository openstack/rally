#!/bin/bash -x

env

mkdir -p .testrepository
python -m subunit.run discover tests/functional > .testrepository/subunit.log

subunit2pyunit < .testrepository/subunit.log
EXIT_CODE=$?
subunit-stats < .testrepository/subunit.log

exit $EXIT_CODE
