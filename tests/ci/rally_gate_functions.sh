#!/usr/bin/env bash

RALLY_DIR=$BASE/new/rally
RALLY_PLUGINS_DIR=~/.rally/plugins
RALLY_EXTRA_DIR=~/.rally/extra

function setUp () {
    set -x

    JOB_DIR=$1

    mkdir -p $RALLY_PLUGINS_DIR
    mkdir -p $RALLY_EXTRA_DIR

    if [ -n "$JOB_DIR" ]; then
        PLUGINS_DIR=${JOB_DIR}/plugins
        EXTRA_DIR=${JOB_DIR}/extra

        if [ -d $PLUGINS_DIR ]; then
            cp -r $PLUGINS_DIR/ $RALLY_PLUGINS_DIR
        fi

        if [ -d $EXTRA_DIR ]; then
         cp -r $EXTRA_DIR/* ~/.rally/extra/
        fi
    fi

    touch ~/.rally/extra/fake-image.img

    env
    set -o pipefail

    rally deployment use --deployment devstack

    source ~/.rally/openrc admin admin

    # NOTE(ikhudoshyn): Create additional users and register a new env
    # so that we could run scenarios using 'existing_users' context
    if [ "$DEVSTACK_GATE_PREPOPULATE_USERS" = "1" ]; then
        # NOTE(andreykurilin): let's hardcode version, since we already
        #    hardcoded arguments for users...
        export OS_IDENTITY_API_VERSION=3
        openstack --version

        openstack project create rally-test-project-1
        openstack user create --project rally-test-project-1 --password rally-test-password-1 rally-test-user-1
        openstack role add --project rally-test-project-1 --user rally-test-user-1 Member

        openstack project create rally-test-project-2
        openstack user create --project rally-test-project-2 --password rally-test-password-2 rally-test-user-2
        openstack role add --project rally-test-project-2 --user rally-test-user-2 Member

        set +e
        NEUTRON_EXISTS=$(openstack --os-interface admin service list | grep neutron)
        set -e
        if [ "$NEUTRON_EXISTS" ]; then
            OS_QUOTA_STR="--networks -1 --subnets -1 --routers -1 --floating-ips -1 --subnetpools -1 --secgroups -1 --secgroup-rules -1 --ports -1"
            openstack --os-interface admin quota set $OS_QUOTA_STR rally-test-project-1
            openstack --os-interface admin quota show rally-test-project-1
            openstack --os-interface admin quota set $OS_QUOTA_STR rally-test-project-2
            openstack --os-interface admin quota show rally-test-project-2
        fi

        DEPLOYMENT_CONFIG_FILE=~/.rally/with-existing-users-config

        rally deployment config > $DEPLOYMENT_CONFIG_FILE
        sed -i '1a    "users": [\
          {\
              "username": "rally-test-user-1",\
              "password": "rally-test-password-1",\
              "project_name": "rally-test-project-1",\
              "user_domain_name": "Default",\
              "project_domain_name": "Default"\
          },\
          {\
              "username": "rally-test-user-2",\
              "password": "rally-test-password-2",\
              "project_name": "rally-test-project-2",\
              "user_domain_name": "Default",\
              "project_domain_name": "Default"\
          }\
        ],\
    ' $DEPLOYMENT_CONFIG_FILE

        rally deployment create --name devstask-with-users --filename $DEPLOYMENT_CONFIG_FILE
    fi

    rally deployment config
    rally --debug deployment check

    if rally deployment check | grep 'nova' | grep 'Available' > /dev/null;
    then
        nova flavor-create m1.nano 42 64 0 1
    fi
}

function run () {
    set -x

    TASK=$1
    TASK_ARGS="$2 $3"
    python $RALLY_DIR/tests/ci/osresources.py --dump-list resources_at_start.txt

    rally --rally-debug task start --task $TASK $TASK_ARGS

    mkdir -p rally-plot/extra
    python $RALLY_DIR/tests/ci/render.py ci/index.html > rally-plot/extra/index.html
    cp $TASK rally-plot/task.txt
    tar -czf rally-plot/plugins.tar.gz -C $RALLY_PLUGINS_DIR .
    rally task results | python -m json.tool > rally-plot/results.json
    gzip -9 rally-plot/results.json
    rally task detailed > rally-plot/detailed.txt
    gzip -9 rally-plot/detailed.txt
    rally task detailed --iterations-data > rally-plot/detailed_with_iterations.txt
    gzip -9 rally-plot/detailed_with_iterations.txt
    rally task report --out rally-plot/results.html
    gzip -9 rally-plot/results.html

    # NOTE(stpierre): if the sla check fails, we still want osresources.py
    # to run, so we turn off -e and save the return value
    set +e
    rally task sla-check | tee rally-plot/sla.txt
    retval=$?
    set -e

    cp resources_at_start.txt rally-plot/
    python $RALLY_DIR/tests/ci/osresources.py\
        --compare-with-list resources_at_start.txt\
            | gzip > rally-plot/resources_diff.txt.gz

    exit $retval
}