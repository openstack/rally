..
      Copyright 2016 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _tutorial_step_10_verifying_cloud_via_tempest:

Step 10. Verifying cloud via Tempest
====================================

.. contents::
   :local:

In this guide, we show how to use Tempest and Rally together.
We assume that you have a :ref:`Rally installation <tutorial_step_0_installation>`
and have already :ref:`registered an OpenStack deployment <tutorial_step_1_setting_up_env_and_running_benchmark_from_samples>`
in Rally. So, let's get started!


Tempest installation (rally verify install/uninstall/reinstall)
---------------------------------------------------------------

Execute the following command to install Tempest:

.. code-block:: console

    $ rally verify install
    2016-05-09 13:23:51.897 21850 INFO rally.verification.tempest.tempest [-] Tempest is not installed for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:23:51.897 21850 INFO rally.verification.tempest.tempest [-] Installing Tempest for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:23:51.908 21850 INFO rally.verification.tempest.tempest [-] Please, wait while Tempest is being cloned.
    Cloning into '/home/ubuntu/.rally/tempest/base/tempest_base-ljZwwS'...
    remote: Counting objects: 70000, done.
    remote: Compressing objects: 100% (37320/37320), done.
    remote: Total 70000 (delta 53645), reused 47857 (delta 32525)
    Receiving objects: 100% (70000/70000), 9.92 MiB | 1.03 MiB/s, done.
    Resolving deltas: 100% (53645/53645), done.
    Checking connectivity... done.
    2016-05-09 13:24:11.180 21850 INFO rally.verification.tempest.tempest [-] Installing the virtual environment for Tempest.
    2016-05-09 13:24:25.596 21850 INFO rally.verification.tempest.tempest [-] Tempest has been successfully installed!

The command clones Tempest from the
**https://git.openstack.org/openstack/tempest** repository and installs it in
a Python virtual environment for the current deployment by default. The
arguments below allow these default behaviors to be overridden.

Use the **--deployment** argument to specify any deployment registered in Rally.

.. code-block:: console

    $ rally verify install --deployment <UUID or name of a deployment>

Use the **--source** argument to specify an alternate git repository location.
The path to a local Tempest repository or a URL of a remote repository are
both valid values.

.. code-block:: console

    $ rally verify install --source /home/ubuntu/tempest/
    2016-05-09 13:29:05.004 22382 INFO rally.verification.tempest.tempest [-] Tempest is not installed for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:29:05.004 22382 INFO rally.verification.tempest.tempest [-] Installing Tempest for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:29:05.013 22382 INFO rally.verification.tempest.tempest [-] Please, wait while Tempest is being cloned.
    Cloning into '/home/ubuntu/.rally/tempest/base/tempest_base-pscTA7'...
    done.
    2016-05-09 13:29:05.902 22382 INFO rally.verification.tempest.tempest [-] Installing the virtual environment for Tempest.
    2016-05-09 13:29:18.052 22382 INFO rally.verification.tempest.tempest [-] Tempest has been successfully installed!

.. code-block:: console

    $ rally verify install --source https://github.com/openstack/tempest.git
    2016-05-09 13:30:15.804 22541 INFO rally.verification.tempest.tempest [-] Tempest is not installed for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:30:15.804 22541 INFO rally.verification.tempest.tempest [-] Installing Tempest for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:30:15.814 22541 INFO rally.verification.tempest.tempest [-] Please, wait while Tempest is being cloned.
    Cloning into '/home/ubuntu/.rally/tempest/base/tempest_base-BLUv1E'...
    remote: Counting objects: 70000, done.
    remote: Compressing objects: 100% (7/7), done.
    remote: Total 70000 (delta 0), reused 0 (delta 0), pack-reused 69993
    Receiving objects: 100% (70000/70000), 20.66 MiB | 2.67 MiB/s, done.
    Resolving deltas: 100% (52246/52246), done.
    Checking connectivity... done.
    2016-05-09 13:30:37.602 22541 INFO rally.verification.tempest.tempest [-] Installing the virtual environment for Tempest.
    2016-05-09 13:30:49.432 22541 INFO rally.verification.tempest.tempest [-] Tempest has been successfully installed!

Use the **--version** argument to specify a Tempest commit ID or tag.

.. code-block:: console

    $ rally verify install --source /home/ubuntu/tempest/ --version 198e5b4b871c3d09c20afb56dca9637a8cf86ac8
    2016-05-09 13:45:55.764 23259 INFO rally.verification.tempest.tempest [-] Tempest is not installed for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:45:55.764 23259 INFO rally.verification.tempest.tempest [-] Installing Tempest for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:45:55.773 23259 INFO rally.verification.tempest.tempest [-] Please, wait while Tempest is being cloned.
    Cloning into '/home/ubuntu/.rally/tempest/base/tempest_base-TcKvAX'...
    done.
    T	doc/source/HACKING.rst
    T	doc/source/REVIEWING.rst
    T	doc/source/field_guide/api.rst
    T	doc/source/field_guide/index.rst
    T	doc/source/field_guide/scenario.rst
    T	doc/source/field_guide/stress.rst
    T	doc/source/field_guide/unit_tests.rst
    T	doc/source/overview.rst
    Note: checking out '198e5b4b871c3d09c20afb56dca9637a8cf86ac8'.

    You are in 'detached HEAD' state. You can look around, make experimental
    changes and commit them, and you can discard any commits you make in this
    state without impacting any branches by performing another checkout.

    If you want to create a new branch to retain commits you create, you may
    do so (now or later) by using -b with the checkout command again. Example:

      git checkout -b new_branch_name

    HEAD is now at 198e5b4... Merge "Pass server to RemoteClient in API tests"
    2016-05-09 13:45:56.061 23259 INFO rally.verification.tempest.tempest [-] Installing the virtual environment for Tempest.
    2016-05-09 13:46:15.278 23259 INFO rally.verification.tempest.tempest [-] Tempest has been successfully installed!

.. code-block:: console

    $ rally verify install --source /home/ubuntu/tempest/ --version 10.0.0
    2016-05-09 13:50:42.559 23870 INFO rally.verification.tempest.tempest [-] Tempest is not installed for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:50:42.559 23870 INFO rally.verification.tempest.tempest [-] Installing Tempest for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:50:42.568 23870 INFO rally.verification.tempest.tempest [-] Please, wait while Tempest is being cloned.
    Cloning into '/home/ubuntu/.rally/tempest/base/tempest_base-cUe5p8'...
    done.
    T	doc/source/HACKING.rst
    T	doc/source/REVIEWING.rst
    T	doc/source/field_guide/api.rst
    T	doc/source/field_guide/index.rst
    T	doc/source/field_guide/scenario.rst
    T	doc/source/field_guide/stress.rst
    T	doc/source/field_guide/unit_tests.rst
    T	doc/source/overview.rst
    Note: checking out '10.0.0'.

    You are in 'detached HEAD' state. You can look around, make experimental
    changes and commit them, and you can discard any commits you make in this
    state without impacting any branches by performing another checkout.

    If you want to create a new branch to retain commits you create, you may
    do so (now or later) by using -b with the checkout command again. Example:

      git checkout -b new_branch_name

    HEAD is now at 09a6015... Merge "Make data_processing/baremetal use rest_client"
    2016-05-09 13:50:42.903 23870 INFO rally.verification.tempest.tempest [-] Installing the virtual environment for Tempest.
    2016-05-09 13:50:55.827 23870 INFO rally.verification.tempest.tempest [-] Tempest has been successfully installed!

Use the **--system-wide** argument to install Tempest in the system Python path.
In this case, it is assumed that all Tempest requirements are already installed
in the local environment.

.. code-block:: console

    $ rally verify install --source /home/ubuntu/tempest/ --version 10.0.0 --system-wide
    2016-05-09 13:52:34.085 24216 INFO rally.verification.tempest.tempest [-] Tempest is not installed for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:52:34.085 24216 INFO rally.verification.tempest.tempest [-] Installing Tempest for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 13:52:34.094 24216 INFO rally.verification.tempest.tempest [-] Please, wait while Tempest is being cloned.
    Cloning into '/home/ubuntu/.rally/tempest/base/tempest_base-8jFGJU'...
    done.
    T	doc/source/HACKING.rst
    T	doc/source/REVIEWING.rst
    T	doc/source/field_guide/api.rst
    T	doc/source/field_guide/index.rst
    T	doc/source/field_guide/scenario.rst
    T	doc/source/field_guide/stress.rst
    T	doc/source/field_guide/unit_tests.rst
    T	doc/source/overview.rst
    Note: checking out '10.0.0'.

    You are in 'detached HEAD' state. You can look around, make experimental
    changes and commit them, and you can discard any commits you make in this
    state without impacting any branches by performing another checkout.

    If you want to create a new branch to retain commits you create, you may
    do so (now or later) by using -b with the checkout command again. Example:

      git checkout -b new_branch_name

    HEAD is now at 09a6015... Merge "Make data_processing/baremetal use rest_client"
    2016-05-09 13:52:34.519 24216 INFO rally.verification.tempest.tempest [-] Tempest has been successfully installed!

To remove a local Tempest installation for the current deployment execute the
following command:

.. code-block:: console

    $ rally verify uninstall

Use the **--deployment** argument to remove the Tempest installation for any
registered deployment in Rally.

.. code-block:: console

    $ rally verify uninstall --deployment <UUID or name of a deployment>

Execute the following command to reinstall Tempest:

.. code-block:: console

    $ rally verify reinstall

This command combines the operations of the uninstall and install commands and
takes the same arguments as **rally verify install**.


Tempest config generation (rally verify genconfig/showconfig)
-------------------------------------------------------------

Execute the following command to generate a Tempest config file for the
current deployment:

.. code-block:: console

    $ rally verify genconfig
    2016-05-09 14:31:48.050 25906 INFO rally.verification.tempest.tempest [-] Tempest is not configured for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 14:31:48.050 25906 INFO rally.verification.tempest.tempest [-] Creating Tempest configuration file for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 14:31:56.738 25906 INFO rally.verification.tempest.tempest [-] Tempest configuration file has been successfully created!

Use the **--deployment** argument to generate the config file for any
deployment registered in Rally

.. code-block:: console

    $ rally verify genconfig --deployment <UUID or name of a deployment>

Provide a file path argument to specify the path of the generated config file.
In the example below, the config file will be written to
``/home/ubuntu/tempest.conf``.

.. code-block:: console

    $ rally verify genconfig --tempest-config /home/ubuntu/tempest.conf
    2016-05-09 14:34:07.619 26204 INFO rally.verification.tempest.tempest [-] Tempest is not configured for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 14:34:07.619 26204 INFO rally.verification.tempest.tempest [-] Creating Tempest configuration file for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 14:34:09.449 26204 INFO rally.verification.tempest.tempest [-] Tempest configuration file has been successfully created!

Moreover, it is possible to override the existing Tempest config file by
providing the **--override** argument in the **rally verify genconfig**
command:

.. code-block:: console

    $ rally verify genconfig --override
    2016-05-09 14:35:11.608 26270 INFO rally.verification.tempest.tempest [-] Creating Tempest configuration file for deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 14:35:13.395 26270 INFO rally.verification.tempest.tempest [-] Tempest configuration file has been successfully created!

In order to see the generated config file execute the following command:

.. code-block:: console

    $ rally verify showconfig
    Tempest config file: /home/ubuntu/.rally/tempest/for-deployment-452f3c6b-119a-4054-a6aa-e4e3347824de/tempest.conf

    [DEFAULT]
    debug = True
    log_file = tempest.log
    use_stderr = False

    [auth]
    use_dynamic_credentials = True
    ...

To see the generated config file for a certain deployment specify the
**--deployment** argument.

.. code-block:: console

    $ rally verify showconfig --deployment <UUID or name of a deployment>


Start a verification (rally verify start)
-----------------------------------------

In order to start a verification execute the following command:

.. code-block:: console

    $ rally verify start
    2016-05-09 14:54:07.446 27377 INFO rally.api [-] Starting verification of deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 14:54:07.529 27377 INFO rally.verification.tempest.tempest [-] Verification de083a94-8b42-46fe-9cdd-2b6066f9c13c | Starting:  Run verification.
    2016-05-09 14:54:07.613 27377 INFO rally.verification.tempest.tempest [-] Using Tempest config file: /home/ubuntu/.rally/tempest/for-deployment-452f3c6b-119a-4054-a6aa-e4e3347824de/tempest.conf
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover} --list
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpcbg8BK
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpJEOWsG
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpD8Hsxu
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmp2UQC55
    {1} setUpClass (tempest.api.baremetal.admin.test_ports_negative.TestPortsNegative) ... SKIPPED: TestPortsNegative skipped as Ironic is not available
    {2} setUpClass (tempest.api.baremetal.admin.test_api_discovery.TestApiDiscovery) ... SKIPPED: TestApiDiscovery skipped as Ironic is not available
    {2} setUpClass (tempest.api.baremetal.admin.test_chassis.TestChassis) ... SKIPPED: TestChassis skipped as Ironic is not available
    {2} setUpClass (tempest.api.baremetal.admin.test_drivers.TestDrivers) ... SKIPPED: TestDrivers skipped as Ironic is not available
    {3} setUpClass (tempest.api.baremetal.admin.test_nodes.TestNodes) ... SKIPPED: TestNodes skipped as Ironic is not available
    {3} setUpClass (tempest.api.baremetal.admin.test_ports.TestPorts) ... SKIPPED: TestPorts skipped as Ironic is not available
    {0} setUpClass (tempest.api.baremetal.admin.test_nodestates.TestNodeStates) ... SKIPPED: TestNodeStates skipped as Ironic is not available
    {1} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_create_agent [0.712663s] ... ok
    {1} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_delete_agent [0.502782s] ... ok
    {3} tempest.api.compute.admin.test_flavors_access_negative.FlavorsAccessNegativeTestJSON.test_add_flavor_access_duplicate [1.011901s] ... ok
    ...

By default, the command runs the full suite of Tempest tests for the current
deployment, but it is possible to run the tests for any registered deployment
in Rally, using the **--deployment** argument.

.. code-block:: console

    $ rally verify start --deployment <UUID or name of a deployment>

Also, Rally allows users to specify a certain Tempest config file location to
use a certain Tempest config file for running the tests.

.. code-block:: console

    $ rally verify start --tempest-config /home/ubuntu/tempest.conf
    2016-05-09 15:24:02.474 29197 INFO rally.api [-] Starting verification of deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 15:24:02.558 29197 INFO rally.verification.tempest.tempest [-] Verification 85b90b77-ee32-4e56-83ed-aabf306cb509 | Starting:  Run verification.
    2016-05-09 15:24:02.641 29197 INFO rally.verification.tempest.tempest [-] Using Tempest config file: /home/ubuntu/tempest.conf
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover} --list
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpqJcBEn
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmplKu5tZ
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpww2PLm
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmp6ip_UK
    {0} setUpClass (tempest.api.baremetal.admin.test_api_discovery.TestApiDiscovery) ... SKIPPED: TestApiDiscovery skipped as Ironic is not available
    {0} setUpClass (tempest.api.baremetal.admin.test_ports.TestPorts) ... SKIPPED: TestPorts skipped as Ironic is not available
    {0} setUpClass (tempest.api.baremetal.admin.test_ports_negative.TestPortsNegative) ... SKIPPED: TestPortsNegative skipped as Ironic is not available
    {3} setUpClass (tempest.api.baremetal.admin.test_nodestates.TestNodeStates) ... SKIPPED: TestNodeStates skipped as Ironic is not available
    {3} setUpClass (tempest.api.compute.admin.test_fixed_ips.FixedIPsTestJson) ... SKIPPED: FixedIPsTestJson skipped as neutron is available
    {1} setUpClass (tempest.api.baremetal.admin.test_chassis.TestChassis) ... SKIPPED: TestChassis skipped as Ironic is not available
    {1} setUpClass (tempest.api.baremetal.admin.test_drivers.TestDrivers) ... SKIPPED: TestDrivers skipped as Ironic is not available
    {1} setUpClass (tempest.api.baremetal.admin.test_nodes.TestNodes) ... SKIPPED: TestNodes skipped as Ironic is not available
    {3} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_using_string_ram [0.642174s] ... ok
    {0} tempest.api.compute.admin.test_aggregates_negative.AggregatesAdminNegativeTestJSON.test_aggregate_add_existent_host [1.069448s] ... ok

Also, there is a possibility to run a certain suite of Tempest tests, using
the **--set** argument.

.. code-block:: console

    $ rally verify start --set compute
    2016-05-09 14:56:45.258 27685 INFO rally.api [-] Starting verification of deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 14:56:45.342 27685 INFO rally.verification.tempest.tempest [-] Verification ab0acb96-f664-438a-8323-198fe68d8a96 | Starting:  Run verification.
    2016-05-09 14:56:45.425 27685 INFO rally.verification.tempest.tempest [-] Using Tempest config file: /home/ubuntu/.rally/tempest/for-deployment-452f3c6b-119a-4054-a6aa-e4e3347824de/tempest.conf
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover} --list
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpm1QuaD
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpxmGWlN
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpsaG1BU
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpbZzU2y
    {2} tempest.api.compute.admin.test_aggregates_negative.AggregatesAdminNegativeTestJSON.test_aggregate_add_existent_host [1.623109s] ... ok
    {3} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az [1.125569s] ... FAILED
    {2} tempest.api.compute.admin.test_aggregates_negative.AggregatesAdminNegativeTestJSON.test_aggregate_add_host_as_user [2.267328s] ... ok
    {1} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_create_agent [2.507743s] ... ok
    {0} tempest.api.compute.admin.test_availability_zone.AZAdminV2TestJSON.test_get_availability_zone_list [1.132218s] ... ok
    {0} tempest.api.compute.admin.test_availability_zone.AZAdminV2TestJSON.test_get_availability_zone_list_detail [0.518452s] ... ok
    {1} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_delete_agent [0.796207s] ... ok
    {1} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_list_agents [0.735133s] ... ok
    {2} tempest.api.compute.admin.test_aggregates_negative.AggregatesAdminNegativeTestJSON.test_aggregate_add_non_exist_host [1.941015s] ... ok
    {2} tempest.api.compute.admin.test_aggregates_negative.AggregatesAdminNegativeTestJSON.test_aggregate_create_aggregate_name_length_exceeds_255 [0.183736s] ... ok
    ...

For now, available sets are **full**, **scenario**, **smoke**, **baremetal**,
**compute**, **database**, **data_processing**, **identity**, **image**,
**messaging**, **network**, **object_storage**, **orchestration**,
**telemetry**, **volume**.

Moreover, users can run a certain set of tests, using the **--regex** argument
and specifying a regular expression.

.. code-block:: console

    $ rally verify start --regex tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON
    2016-05-09 15:04:50.089 28117 INFO rally.api [-] Starting verification of deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 15:04:50.173 28117 INFO rally.verification.tempest.tempest [-] Verification 32348bcc-edf1-4434-a10b-9449e2370a16 | Starting:  Run verification.
    2016-05-09 15:04:50.257 28117 INFO rally.verification.tempest.tempest [-] Using Tempest config file: /home/ubuntu/.rally/tempest/for-deployment-452f3c6b-119a-4054-a6aa-e4e3347824de/tempest.conf
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover} --list
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmp3QMRkn
    {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_using_string_ram [0.574063s] ... ok
    {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_verify_entry_in_list_details [0.539422s] ... ok
    {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_int_id [0.542389s] ... ok
    {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_none_id [0.525429s] ... ok
    {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_uuid_id [0.539657s] ... ok
    {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_list_flavor_without_extra_data [0.782256s] ... ok
    {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_server_with_non_public_flavor [0.536828s] ... ok
    {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_is_public_string_variations [1.931141s] ... ok
    {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_list_non_public_flavor [0.691936s] ... ok
    {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_list_public_flavor_with_other_user [0.569325s] ... ok

    ======
    Totals
    ======
    Ran: 10 tests in 18.0000 sec.
     - Passed: 10
     - Skipped: 0
     - Expected Fail: 0
     - Unexpected Success: 0
     - Failed: 0
    Sum of execute time for each test: 7.2324 sec.

    ==============
    Worker Balance
    ==============
     - Worker 0 (10 tests) => 0:00:07.236862
    2016-05-09 15:05:10.473 28117 INFO rally.verification.tempest.tempest [-] Verification 32348bcc-edf1-4434-a10b-9449e2370a16 | Completed: Run verification.
    2016-05-09 15:05:10.474 28117 INFO rally.verification.tempest.tempest [-] Verification 32348bcc-edf1-4434-a10b-9449e2370a16 | Starting:  Saving verification results.
    2016-05-09 15:05:10.677 28117 INFO rally.verification.tempest.tempest [-] Verification 32348bcc-edf1-4434-a10b-9449e2370a16 | Completed: Saving verification results.
    Verification UUID: 32348bcc-edf1-4434-a10b-9449e2370a16

In such a way it is possible to run tests from a certain directory or class
and even run a single test.

.. code-block:: console

    $ rally verify start --regex tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_using_string_ram
    2016-05-09 15:06:18.088 28217 INFO rally.api [-] Starting verification of deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 15:06:18.170 28217 INFO rally.verification.tempest.tempest [-] Verification dbd4bc2d-2b76-42b7-b737-fce86a92fbfa | Starting:  Run verification.
    2016-05-09 15:06:18.254 28217 INFO rally.verification.tempest.tempest [-] Using Tempest config file: /home/ubuntu/.rally/tempest/for-deployment-452f3c6b-119a-4054-a6aa-e4e3347824de/tempest.conf
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover} --list
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpoEkv6Q
    {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_using_string_ram [0.547252s] ... ok

    ======
    Totals
    ======
    Ran: 1 tests in 10.0000 sec.
     - Passed: 1
     - Skipped: 0
     - Expected Fail: 0
     - Unexpected Success: 0
     - Failed: 0
    Sum of execute time for each test: 0.5473 sec.

    ==============
    Worker Balance
    ==============
     - Worker 0 (1 tests) => 0:00:00.547252
    2016-05-09 15:06:31.207 28217 INFO rally.verification.tempest.tempest [-] Verification dbd4bc2d-2b76-42b7-b737-fce86a92fbfa | Completed: Run verification.
    2016-05-09 15:06:31.207 28217 INFO rally.verification.tempest.tempest [-] Verification dbd4bc2d-2b76-42b7-b737-fce86a92fbfa | Starting:  Saving verification results.
    2016-05-09 15:06:31.750 28217 INFO rally.verification.tempest.tempest [-] Verification dbd4bc2d-2b76-42b7-b737-fce86a92fbfa | Completed: Saving verification results.
    Verification UUID: dbd4bc2d-2b76-42b7-b737-fce86a92fbfa

Also, there is a possibility to run Tempest tests from a file. Users can
specify a list of tests in the file and run them, using the **--tests-file**
argument:

.. code-block:: console

    $ cat some-file.txt
    tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_create_agent[id-1fc6bdc8-0b6d-4cc7-9f30-9b04fabe5b90]
    tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_delete_agent[id-470e0b89-386f-407b-91fd-819737d0b335]
    tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_list_agents[id-6a326c69-654b-438a-80a3-34bcc454e138]
    tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_list_agents_with_filter[id-eabadde4-3cd7-4ec4-a4b5-5a936d2d4408]
    tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_update_agent[id-dc9ffd51-1c50-4f0e-a820-ae6d2a568a9e]
    tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_get_details[id-eeef473c-7c52-494d-9f09-2ed7fc8fc036]
    tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_list[id-7f6a1cc5-2446-4cdb-9baa-b6ae0a919b72]
    tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_remove_host[id-c8e85064-e79b-4906-9931-c11c24294d02]
    tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_delete[id-0d148aa3-d54c-4317-aa8d-42040a475e20]

.. code-block:: console

    $ rally verify start --tests-file some-file.txt
    2016-05-09 15:09:10.864 28456 INFO rally.api [-] Starting verification of deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 15:09:10.948 28456 INFO rally.verification.tempest.tempest [-] Verification 526b0c54-3805-48eb-8a04-4fec0aad3fe5 | Starting:  Run verification.
    2016-05-09 15:09:11.033 28456 INFO rally.verification.tempest.tempest [-] Using Tempest config file: /home/ubuntu/.rally/tempest/for-deployment-452f3c6b-119a-4054-a6aa-e4e3347824de/tempest.conf
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpjHUGip
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmp358n_n
    {1} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_create_agent [0.601839s] ... ok
    {1} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_delete_agent [0.501781s] ... ok
    {1} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_list_agents [0.375056s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_get_details [1.036974s] ... ok
    {1} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_list_agents_with_filter [0.640392s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_list [0.850647s] ... ok
    {1} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_update_agent [0.371227s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_remove_host [0.803282s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_delete [0.635170s] ... ok

    ======
    Totals
    ======
    Ran: 9 tests in 11.0000 sec.
     - Passed: 9
     - Skipped: 0
     - Expected Fail: 0
     - Unexpected Success: 0
     - Failed: 0
    Sum of execute time for each test: 5.8164 sec.

    ==============
    Worker Balance
    ==============
     - Worker 0 (4 tests) => 0:00:03.328229
     - Worker 1 (5 tests) => 0:00:02.492475
    2016-05-09 15:09:24.668 28456 INFO rally.verification.tempest.tempest [-] Verification 526b0c54-3805-48eb-8a04-4fec0aad3fe5 | Completed: Run verification.
    2016-05-09 15:09:24.669 28456 INFO rally.verification.tempest.tempest [-] Verification 526b0c54-3805-48eb-8a04-4fec0aad3fe5 | Starting:  Saving verification results.
    2016-05-09 15:09:24.872 28456 INFO rally.verification.tempest.tempest [-] Verification 526b0c54-3805-48eb-8a04-4fec0aad3fe5 | Completed: Saving verification results.
    Verification UUID: 526b0c54-3805-48eb-8a04-4fec0aad3fe5

Sometimes users may want to use the specific concurrency for running tests
based on their deployments and available resources. In this case, they can use
the **--concurrency** argument to specify how many processes to use to run
Tempest tests. The default value (0) auto-detects CPU count.

.. code-block:: console

    $ rally verify start --tests-file some-file.txt --concurrency 1
    2016-05-09 15:10:39.050 28744 INFO rally.api [-] Starting verification of deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 15:10:39.132 28744 INFO rally.verification.tempest.tempest [-] Verification 95fef399-0cfa-4843-ad50-b5ed974928dc | Starting:  Run verification.
    2016-05-09 15:10:39.216 28744 INFO rally.verification.tempest.tempest [-] Using Tempest config file: /home/ubuntu/.rally/tempest/for-deployment-452f3c6b-119a-4054-a6aa-e4e3347824de/tempest.conf
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpl_FWjP
    {0} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_create_agent [0.586906s] ... ok
    {0} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_delete_agent [0.499466s] ... ok
    {0} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_list_agents [0.370536s] ... ok
    {0} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_list_agents_with_filter [0.620824s] ... ok
    {0} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_update_agent [0.365948s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_get_details [0.942561s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_list [0.897054s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_remove_host [0.743319s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_delete [0.629131s] ... ok

    ======
    Totals
    ======
    Ran: 9 tests in 16.0000 sec.
     - Passed: 9
     - Skipped: 0
     - Expected Fail: 0
     - Unexpected Success: 0
     - Failed: 0
    Sum of execute time for each test: 5.6557 sec.

    ==============
    Worker Balance
    ==============
     - Worker 0 (9 tests) => 0:00:09.701447
    2016-05-09 15:10:57.861 28744 INFO rally.verification.tempest.tempest [-] Verification 95fef399-0cfa-4843-ad50-b5ed974928dc | Completed: Run verification.
    2016-05-09 15:10:57.861 28744 INFO rally.verification.tempest.tempest [-] Verification 95fef399-0cfa-4843-ad50-b5ed974928dc | Starting:  Saving verification results.
    2016-05-09 15:10:58.173 28744 INFO rally.verification.tempest.tempest [-] Verification 95fef399-0cfa-4843-ad50-b5ed974928dc | Completed: Saving verification results.
    Verification UUID: 95fef399-0cfa-4843-ad50-b5ed974928dc

Sometimes users may want to re-run only those tests that failed in the last
verification. In order to re-run failed tests in the last verification execute
the following command:

.. code-block:: console

    $ rally verify start --failing

For example, we have one failed test:

.. code-block:: console

    $ rally verify start --regex tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON
    2016-05-09 15:32:39.666 29727 INFO rally.api [-] Starting verification of deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 15:32:39.751 29727 INFO rally.verification.tempest.tempest [-] Verification 1a71f82c-e59d-4b8f-9abd-8a98f53c2531 | Starting:  Run verification.
    2016-05-09 15:32:39.836 29727 INFO rally.verification.tempest.tempest [-] Using Tempest config file: /home/ubuntu/.rally/tempest/for-deployment-452f3c6b-119a-4054-a6aa-e4e3347824de/tempest.conf
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover} --list
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpFQO_SW
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az [0.572658s] ... FAILED
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_get_details [0.877286s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_list [0.938150s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_remove_host [0.902238s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_delete [0.633860s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_delete_with_az [0.654307s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_update_metadata_get_details [0.792414s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_update_with_az [0.823757s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_verify_entry_in_list [0.505302s] ... ok

    ==============================
    Failed 1 tests - output below:
    ==============================

    tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az[id-96be03c7-570d-409c-90f8-e4db3c646996]
    --------------------------------------------------------------------------------------------------------------------------------------------------------

    Captured traceback:
    ~~~~~~~~~~~~~~~~~~~
        Traceback (most recent call last):
          File "tempest/api/compute/admin/test_aggregates.py", line 214, in test_aggregate_add_host_create_server_with_az
            self.client.add_host(aggregate['id'], host=self.host)
          File "tempest/lib/services/compute/aggregates_client.py", line 92, in add_host
            post_body)
          File "tempest/lib/common/rest_client.py", line 259, in post
            return self.request('POST', url, extra_headers, headers, body)
          File "tempest/lib/services/compute/base_compute_client.py", line 53, in request
            method, url, extra_headers, headers, body)
          File "tempest/lib/common/rest_client.py", line 641, in request
            resp, resp_body)
          File "tempest/lib/common/rest_client.py", line 709, in _error_checker
            raise exceptions.Conflict(resp_body, resp=resp)
        tempest.lib.exceptions.Conflict: An object with that identifier already exists
        Details: {u'message': u'Cannot add host node-2.domain.tld in aggregate 422: host exists', u'code': 409}
        ...

Now let's re-run it.

.. code-block:: console

    $ rally verify start --failing
    2016-05-09 15:36:17.389 30104 INFO rally.api [-] Starting verification of deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 15:36:17.474 30104 INFO rally.verification.tempest.tempest [-] Verification f4e857a7-f032-452c-9ffb-dc42f0d2e124 | Starting:  Run verification.
    2016-05-09 15:36:17.559 30104 INFO rally.verification.tempest.tempest [-] Using Tempest config file: /home/ubuntu/.rally/tempest/for-deployment-452f3c6b-119a-4054-a6aa-e4e3347824de/tempest.conf
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmpiYREcb
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az [0.665381s] ... FAILED

    ==============================
    Failed 1 tests - output below:
    ==============================

    tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az[id-96be03c7-570d-409c-90f8-e4db3c646996]
    --------------------------------------------------------------------------------------------------------------------------------------------------------

    Captured traceback:
    ~~~~~~~~~~~~~~~~~~~
        Traceback (most recent call last):
          File "tempest/api/compute/admin/test_aggregates.py", line 214, in test_aggregate_add_host_create_server_with_az
            self.client.add_host(aggregate['id'], host=self.host)
          File "tempest/lib/services/compute/aggregates_client.py", line 92, in add_host
            post_body)
          File "tempest/lib/common/rest_client.py", line 259, in post
            return self.request('POST', url, extra_headers, headers, body)
          File "tempest/lib/services/compute/base_compute_client.py", line 53, in request
            method, url, extra_headers, headers, body)
          File "tempest/lib/common/rest_client.py", line 641, in request
            resp, resp_body)
          File "tempest/lib/common/rest_client.py", line 709, in _error_checker
            raise exceptions.Conflict(resp_body, resp=resp)
        tempest.lib.exceptions.Conflict: An object with that identifier already exists
        Details: {u'message': u'Cannot add host node-2.domain.tld in aggregate 431: host exists', u'code': 409}
        ...

Also, it is possible to specify the path to a YAML file with a list of Tempest
tests that are expected to fail. In this case, the specified test will have the
**xfail** status instead of **fail** in the verification report. How to build
a verification report we tell you bellow.

.. code-block:: console

    $ cat xfails-file.yaml
    tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az[id-96be03c7-570d-409c-90f8-e4db3c646996]: Some reason why the test fails

.. code-block:: console

    $ rally verify start --regex tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON --xfails-file xfails-file.yaml
    2016-05-09 16:31:36.236 772 INFO rally.api [-] Starting verification of deployment: 452f3c6b-119a-4054-a6aa-e4e3347824de
    2016-05-09 16:31:36.320 772 INFO rally.verification.tempest.tempest [-] Verification 76d41e5d-bf24-4e16-a9ae-5a722f8fad05 | Starting:  Run verification.
    2016-05-09 16:31:36.402 772 INFO rally.verification.tempest.tempest [-] Using Tempest config file: /home/ubuntu/.rally/tempest/for-deployment-452f3c6b-119a-4054-a6aa-e4e3347824de/tempest.conf
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover} --list
    running=OS_STDOUT_CAPTURE=${OS_STDOUT_CAPTURE:-1} \
    OS_STDERR_CAPTURE=${OS_STDERR_CAPTURE:-1} \
    OS_TEST_TIMEOUT=${OS_TEST_TIMEOUT:-500} \
    OS_TEST_LOCK_PATH=${OS_TEST_LOCK_PATH:-${TMPDIR:-'/tmp'}} \
    ${PYTHON:-python} -m subunit.run discover -t ${OS_TOP_LEVEL:-./} ${OS_TEST_PATH:-./tempest/test_discover}  --load-list /tmp/tmp9sB5u5
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az [0.625294s] ... FAILED
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_get_details [0.897577s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_list [0.865686s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_remove_host [0.710349s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_delete [0.620124s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_delete_with_az [0.642956s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_update_metadata_get_details [0.766061s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_update_with_az [0.795929s] ... ok
    {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_verify_entry_in_list [0.495695s] ... ok

    ==============================
    Failed 1 tests - output below:
    ==============================

    tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az[id-96be03c7-570d-409c-90f8-e4db3c646996]
    --------------------------------------------------------------------------------------------------------------------------------------------------------

    Captured traceback:
    ~~~~~~~~~~~~~~~~~~~
        Traceback (most recent call last):
          File "tempest/api/compute/admin/test_aggregates.py", line 214, in test_aggregate_add_host_create_server_with_az
            self.client.add_host(aggregate['id'], host=self.host)
          File "tempest/lib/services/compute/aggregates_client.py", line 92, in add_host
            post_body)
          File "tempest/lib/common/rest_client.py", line 259, in post
            return self.request('POST', url, extra_headers, headers, body)
          File "tempest/lib/services/compute/base_compute_client.py", line 53, in request
            method, url, extra_headers, headers, body)
          File "tempest/lib/common/rest_client.py", line 641, in request
            resp, resp_body)
          File "tempest/lib/common/rest_client.py", line 709, in _error_checker
            raise exceptions.Conflict(resp_body, resp=resp)
        tempest.lib.exceptions.Conflict: An object with that identifier already exists
        Details: {u'message': u'Cannot add host node-2.domain.tld in aggregate 450: host exists', u'code': 409}
        ...

.. image:: ../images/Report-verify-xfail.png
   :align: center

Finally, users can specify the **--system-wide** argument that will tell Rally
not to use the Tempest virtual environment for tests. In this case, it is
assumed that all Tempest requirements are already installed in the local
environment. This argument is useful when users don't have an Internet
connection to install requirements, but they have pre-installed ones in the
local environment.

.. code-block:: console

    $ rally verify start --system-wide
    ...
