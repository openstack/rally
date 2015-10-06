#!/bin/bash -ex
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compli$OUT with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This script is executed by post_test_hook function in desvstack gate.

RESULTS_DIR="rally-verify"

env
set -o pipefail
set +e

mkdir -p ${RESULTS_DIR}/extra


# Check deployment
rally deployment use --deployment devstack
rally deployment check

function do_status {
    if [[ ${1} != 0 ]]
    then
        echo "fail"
    else
        echo "pass"
    fi
}

declare -a RESULTS

rally --rally-debug verify install > ${RESULTS_DIR}/tempest_installation.txt 2>&1
RESULTS+="install=$(do_status $?) "

rally --rally-debug verify genconfig --tempest-config ${RESULTS_DIR}/tempest.conf > ${RESULTS_DIR}/tempest_config_generation.txt 2>&1
RESULTS+="genconfig=$(do_status $?) "

gzip -9 ${RESULTS_DIR}/tempest_installation.txt
gzip -9 ${RESULTS_DIR}/tempest_config_generation.txt

function do_verification {
    OUTPUT_FILE=${RESULTS_DIR}/${1}_verification_${2}_set.txt
    rally --rally-debug verify start --set ${2} > ${OUTPUT_FILE} 2>&1
    RESULTS+="v${1}=$(do_status $?) "
    gzip -9 ${OUTPUT_FILE}
    source ~/.rally/globals && VERIFICATIONS[${1}]=${RALLY_VERIFICATION}

    # Check different "rally verify" commands, which displays verification results
    for OUTPUT_FORMAT in "html" "json"
    do
        OUTPUT_FILE=${RESULTS_DIR}/${1}_verify_results_${2}_set.${OUTPUT_FORMAT}
        rally verify results --uuid ${RALLY_VERIFICATION} --${OUTPUT_FORMAT} --output-file ${OUTPUT_FILE}
        RESULTS+="vr_${1}_${OUTPUT_FORMAT}=$(do_status $?) "
        gzip -9 ${OUTPUT_FILE}
    done

    rally verify show --uuid ${RALLY_VERIFICATION} > ${RESULTS_DIR}/${1}_verify_show_${2}_set.txt
    RESULTS+="vs_${1}=$(do_status $?) "
    gzip -9 ${RESULTS_DIR}/${1}_verify_show_${2}_set.txt

    rally verify show --uuid ${RALLY_VERIFICATION} --detailed > ${RESULTS_DIR}/${1}_verify_show_${2}_set_detailed.txt
    RESULTS+="vsd_${1}=$(do_status $?) "
    gzip -9 ${RESULTS_DIR}/${1}_verify_show_${2}_set_detailed.txt
}

function main {
    do_verification 1 compute
    do_verification 2 compute

    rally verify list > ${RESULTS_DIR}/verify_list.txt
    RESULTS+="l=$(do_status $?) "
    gzip -9 ${RESULTS_DIR}/verify_list.txt

    # Compare and save results in different formats
    for OUTPUT_FORMAT in "csv" "html" "json"
    do
        OUTPUT_FILE=${RESULTS_DIR}/compare_results.${OUTPUT_FORMAT}
        rally --rally-debug verify compare --uuid-1 ${VERIFICATIONS[1]} --uuid-2 ${VERIFICATIONS[2]} --${OUTPUT_FORMAT} --output-file ${OUTPUT_FILE}
        RESULTS+="c_${OUTPUT_FORMAT}=$(do_status $?) "
        gzip -9 ${OUTPUT_FILE}
    done

    python $BASE/new/rally/rally/ui/utils.py render\
        tests/ci/rally-gate/index_verify.mako ${RESULTS[*]}> ${RESULTS_DIR}/extra/index.html

    if [[ ${RESULTS[*]} == *"fail"* ]]
    then
        return 1
    fi

    RESULT_USE=$(rally verify use --verification ${VERIFICATIONS[1]})
    if [ "$RESULT_USE" != "Verification UUID: ${VERIFICATIONS[1]}" ]
    then
        return 1
    fi
}

main "$@"
