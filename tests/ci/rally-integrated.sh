#!/bin/bash -x

env

LOG=.testrepository/subunit.log

mkdir -p .testrepository

date "+Start tests at %Y-%m-%d %H:%M:%S"

python -m subunit.run discover tests/functional | tee ${LOG} | subunit2pyunit

cat ${LOG} | subunit-stats

cat ${LOG} | subunit-stats | grep -Eq "^Failed tests:      0$"
