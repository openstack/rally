#!/bin/bash

# Current scriipt is the simple wrapper on common tools/run_tests_common.sh
# scrip. It pass project specific variables to common script.
#
# Optins list (from tools/run_tests_common.sh).
# Use `./run_tests.sh -h` `./run_tests.sh --help` to get help message
#
#  -V, --virtual-env          Always use virtualenv. Install automatically if not present
#  -N, --no-virtual-env       Don't use virtualenv. Run tests in local environment
#  -s, --no-site-packages     Isolate the virtualenv from the global Python environment
#  -r, --recreate-db          Recreate the test database (deprecated, as this is now the default).
#  -n, --no-recreate-db       Don't recreate the test database.
#  -f, --force                Force a clean re-build of the virtual environment. Useful when dependencies have been added.
#  -u, --update               Update the virtual environment with any newer package versions
#  -p, --pep8                 Just run PEP8 and HACKING compliance check
#  -P, --no-pep8              Don't run static code checks
#  -c, --coverage             Generate coverage report
#  -d, --debug                Run tests with testtools instead of testr. This allows you to use the debugger.
#  -h, --help                 Print this usage message
#  --hide-elapsed             Don't print the elapsed time for each test along with slow test list
#  --virtual-env-path <path>  Location of the virtualenv directory. Default: \$(pwd)
#  --virtual-env-name <name>  Name of the virtualenv directory. Default: .venv
#  --tools-path <dir>         Location of the tools directory. Default: \$(pwd)
#
#  Note: with no options specified, the script will try to run the tests in a
#        virtual environment, if no virtualenv is found, the script will ask if
#        you would like to create one.  If you prefer to run tests NOT in a
#        virtual environment, simply pass the -N option.


# On Linux, testrepository will inspect /proc/cpuinfo to determine how many
# CPUs are present in the machine, and run one worker per CPU.
# Set workers_count=0 if you want to run one worker per CPU.
# Make our paths available to run_tests_common.sh using `export` statement
# export WORKERS_COUNT=0

# there are no possibility to run some oslo tests with concurrency > 1
# or separately due to dependencies between tests (see bug 1192207)
export WORKERS_COUNT=1
# option include {PROJECT_NAME}/* directory to coverage report if `-c` or
# `--coverage` uses
export PROJECT_NAME="rally"
# option exclude "${PROJECT_NAME}/openstack/common/*" from coverage report
# if equals to 1
export OMIT_OSLO_FROM_COVERAGE=0
# path to directory with tests
export TESTS_DIR="tests/"
export EGG_INFO_FILE="rally.egg-info/entry_points.txt"

# run common test script
tools/run_tests_common.sh $*
