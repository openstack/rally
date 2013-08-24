#!/bin/bash

set -eu

function usage {
  echo "Usage: $0 [OPTION]..."
  echo "Run project's test suite(s)"
  echo ""
  echo "  -V, --virtual-env           Always use virtualenv.  Install automatically if not present"
  echo "  -N, --no-virtual-env        Don't use virtualenv.  Run tests in local environment"
  echo "  -s, --no-site-packages      Isolate the virtualenv from the global Python environment"
  echo "  -r, --recreate-db           Recreate the test database (deprecated, as this is now the default)."
  echo "  -n, --no-recreate-db        Don't recreate the test database."
  echo "  -f, --force                 Force a clean re-build of the virtual environment. Useful when dependencies have been added."
  echo "  -u, --update                Update the virtual environment with any newer package versions"
  echo "  -p, --pep8                  Just run PEP8 and HACKING compliance check"
  echo "  -P, --no-pep8               Don't run static code checks"
  echo "  -c, --coverage              Generate coverage report"
  echo "  -d, --debug                 Run tests with testtools instead of testr. This allows you to use the debugger."
  echo "  -h, --help                  Print this usage message"
  echo "  --hide-elapsed              Don't print the elapsed time for each test along with slow test list"
  echo "  --virtual-env-path <path>   Location of the virtualenv directory"
  echo "                               Default: \$(pwd)"
  echo "  --virtual-env-name <name>   Name of the virtualenv directory"
  echo "                               Default: .venv"
  echo "  --tools-path <dir>          Location of the tools directory"
  echo "                               Default: \$(pwd)"
  echo ""
  echo "Note: with no options specified, the script will try to run the tests in a virtual environment,"
  echo "      If no virtualenv is found, the script will ask if you would like to create one.  If you "
  echo "      prefer to run tests NOT in a virtual environment, simply pass the -N option."
  exit
}

function process_options {
  i=1
  while [ $i -le $# ]; do
    case "${!i}" in
      -h|--help) usage;;
      -V|--virtual-env) ALWAYS_VENV=1; NEVER_VENV=0;;
      -N|--no-virtual-env) ALWAYS_VENV=0; NEVER_VENV=1;;
      -s|--no-site-packages) NO_SITE_PACKAGES=1;;
      -r|--recreate-db) RECREATE_DB=1;;
      -n|--no-recreate-db) RECREATE_DB=0;;
      -f|--force) FORCE=1;;
      -u|--update) UPDATE=1;;
      -p|--pep8) JUST_PEP8=1;;
      -P|--no-pep8) NO_PEP8=1;;
      -c|--coverage) COVERAGE=1;;
      -d|--debug) DEBUG=1;;
      --virtual-env-path)
        (( i++ ))
        VENV_PATH=${!i}
        ;;
      --virtual-env-name)
        (( i++ ))
        VENV_DIR=${!i}
        ;;
      --tools-path)
        (( i++ ))
        TOOLS_PATH=${!i}
        ;;
      -*) TESTOPTS="$TESTOPTS ${!i}";;
      *) TESTRARGS="$TESTRARGS ${!i}"
    esac
    (( i++ ))
  done
}


TOOLS_PATH=${TOOLS_PATH:-${PWD}}
VENV_PATH=${VENV_PATH:-${PWD}}
VENV_DIR=${VENV_NAME:-.venv}
WITH_VENV=${TOOLS_PATH}/tools/with_venv.sh

ALWAYS_VENV=0
NEVER_VENV=0
FORCE=0
NO_SITE_PACKAGES=1
INSTALLVENVOPTS=
TESTRARGS=
TESTOPTS=
WRAPPER=""
JUST_PEP8=0
NO_PEP8=0
COVERAGE=0
DEBUG=0
RECREATE_DB=1
UPDATE=0

LANG=en_US.UTF-8
LANGUAGE=en_US:en
LC_ALL=C

process_options $@
# Make our paths available to other scripts we call
export VENV_PATH
export TOOLS_PATH
export VENV_DIR
export VENV_NAME
export WITH_VENV
export VENV=${VENV_PATH}/${VENV_DIR}

function init_testr {
  if [ ! -d .testrepository ]; then
    ${WRAPPER} testr init
  fi
}

function run_tests {
  # Cleanup *pyc
  ${WRAPPER} find . -type f -name "*.pyc" -delete

  if [ ${DEBUG} -eq 1 ]; then
    if [ "${TESTOPTS}" = "" ] && [ "${TESTRARGS}" = "" ]; then
      # Default to running all tests if specific test is not
      # provided.
      TESTRARGS="discover ./${TESTS_DIR}"
    fi
    ${WRAPPER} python -m testtools.run ${TESTOPTS} ${TESTRARGS}

    # Short circuit because all of the testr and coverage stuff
    # below does not make sense when running testtools.run for
    # debugging purposes.
    return $?
  fi

  if [ ${COVERAGE} -eq 1 ]; then
    TESTRTESTS="${TESTRTESTS} --coverage"
  else
    TESTRTESTS="${TESTRTESTS}"
  fi

  # Just run the test suites in current environment
  set +e
  TESTRARGS=`echo "${TESTRARGS}" | sed -e's/^\s*\(.*\)\s*$/\1/'`

  if [ ${WORKERS_COUNT} -ne 0 ]; then
    TESTRTESTS="${TESTRTESTS} --testr-args='--concurrency=${WORKERS_COUNT} --subunit ${TESTOPTS} ${TESTRARGS}'"
  else
    TESTRTESTS="${TESTRTESTS} --testr-args='--subunit ${TESTOPTS} ${TESTRARGS}'"
  fi

  if [ setup.cfg -nt ${EGG_INFO_FILE} ]; then
    ${WRAPPER} python setup.py egg_info
  fi

  echo "Running \`${WRAPPER} ${TESTRTESTS}\`"
  if ${WRAPPER} which subunit-2to1 2>&1 > /dev/null; then
    # subunit-2to1 is present, testr subunit stream should be in version 2
    # format. Convert to version one before colorizing.
    bash -c "${WRAPPER} ${TESTRTESTS} | ${WRAPPER} subunit-2to1 | ${WRAPPER} ${TOOLS_PATH}/tools/colorizer.py"
  else
    bash -c "${WRAPPER} ${TESTRTESTS} | ${WRAPPER} ${TOOLS_PATH}/tools/colorizer.py"
  fi
  RESULT=$?
  set -e

  copy_subunit_log

  if [ $COVERAGE -eq 1 ]; then
    echo "Generating coverage report in covhtml/"
    ${WRAPPER} coverage combine
    # Don't compute coverage for common code, which is tested elsewhere
    # if we are not in `oslo-incubator` project
    if [ ${OMIT_OSLO_FROM_COVERAGE} -eq 0 ]; then
        OMIT_OSLO=""
    else
        OMIT_OSLO="--omit='${PROJECT_NAME}/openstack/common/*'"
    fi
    ${WRAPPER} coverage html --include='${PROJECT_NAME}/*' ${OMIT_OSLO} -d covhtml -i
  fi

  return ${RESULT}
}

function copy_subunit_log {
  LOGNAME=`cat .testrepository/next-stream`
  LOGNAME=$((${LOGNAME} - 1))
  LOGNAME=".testrepository/${LOGNAME}"
  cp ${LOGNAME} subunit.log
}

function run_pep8 {
  echo "Running flake8 ..."
  bash -c "${WRAPPER} flake8"
}


TESTRTESTS="python setup.py testr"

if [ ${NO_SITE_PACKAGES} -eq 1 ]; then
  INSTALLVENVOPTS="--no-site-packages"
fi

if [ ${NEVER_VENV} -eq 0 ]; then
  # Remove the virtual environment if -f or --force used
  if [ ${FORCE} -eq 1 ]; then
    echo "Cleaning virtualenv..."
    rm -rf ${VENV}
  fi

  # Update the virtual environment if -u or --update used
  if [ ${UPDATE} -eq 1 ]; then
      echo "Updating virtualenv..."
      python ${TOOLS_PATH}/tools/install_venv.py ${INSTALLVENVOPTS}
  fi

  if [ -e ${VENV} ]; then
    WRAPPER="${WITH_VENV}"
  else
    if [ ${ALWAYS_VENV} -eq 1 ]; then
      # Automatically install the virtualenv
      python ${TOOLS_PATH}/tools/install_venv.py ${INSTALLVENVOPTS}
      WRAPPER="${WITH_VENV}"
    else
      echo -e "No virtual environment found...create one? (Y/n) \c"
      read USE_VENV
      if [ "x${USE_VENV}" = "xY" -o "x${USE_VENV}" = "x" -o "x${USE_VENV}" = "xy" ]; then
        # Install the virtualenv and run the test suite in it
        python ${TOOLS_PATH}/tools/install_venv.py ${INSTALLVENVOPTS}
        WRAPPER=${WITH_VENV}
      fi
    fi
  fi
fi

# Delete old coverage data from previous runs
if [ ${COVERAGE} -eq 1 ]; then
    ${WRAPPER} coverage erase
fi

if [ ${JUST_PEP8} -eq 1 ]; then
    run_pep8
    exit
fi

if [ ${RECREATE_DB} -eq 1 ]; then
    rm -f tests.sqlite
fi

init_testr
run_tests

# NOTE(sirp): we only want to run pep8 when we're running the full-test suite,
# not when we're running tests individually. To handle this, we need to
# distinguish between options (testropts), which begin with a '-', and
# arguments (testrargs).
if [ -z "${TESTRARGS}" ]; then
  if [ ${NO_PEP8} -eq 0 ]; then
    run_pep8
  fi
fi
