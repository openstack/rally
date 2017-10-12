#!/usr/bin/env bash

LOCAL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

DB_CONNECTION="$(rally db show)"

if [[ $DB_CONNECTION == sqlite* ]]; then
    CONCURRENCY=0
else
    # in case of not sqlite db backends we cannot launch tests in parallel due
    # to possible conflicts
    CONCURRENCY=1
    # currently, RCI_KEEP_DB variable is used to not create new databases per
    # each test
    export RCI_KEEP_DB=1
fi


python $LOCAL_DIR/pytest_launcher.py "tests/functional" --concurrency $CONCURRENCY --posargs=$1
