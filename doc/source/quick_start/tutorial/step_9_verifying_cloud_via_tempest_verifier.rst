..
      Copyright 2017 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _tutorial_step_9_verifying_cloud_via_tempest_verifier:

Step 9. Verifying cloud via Tempest verifier
============================================

.. contents::
   :local:

As you may know, Rally has a verification component (aka **'rally verify'**).
Earlier the purpose of this component was to simplify work with
`Tempest <https://github.com/openstack/tempest>`_ framework (The OpenStack
Integration Test Suite). Rally provided a quite simple interface to install and
configure Tempest, run tests and build a report with results. But now the
verification component allows us to simplify work not only with Tempest but
also with any test frameworks or tools. All you need is to create a plugin for
your framework or tool, and you will be able to use **'rally verify'**
interface for it. At this point, Rally supports only one plugin in the
verification component out of the box - as you might guess, Tempest plugin. In
this guide, we will show how to use Tempest and Rally together via the updated
**'rally verify'** interface. We assume that you already have a
:ref:`Rally installation <tutorial_step_0_installation>` and have already
:ref:`registered an OpenStack deployment <tutorial_step_1_setting_up_env_and_running_benchmark_from_samples>`
in Rally. So, let's get started!


Create/delete Tempest verifier
------------------------------

Execute the following command to create a Tempest verifier:

.. code-block:: console

    $ rally verify create-verifier --type tempest --name tempest-verifier
    2017-01-18 14:43:20.807 5125 INFO rally.api [-] Creating verifier 'tempest-verifier'.
    2017-01-18 14:43:21.203 5125 INFO rally.verification.manager [-] Cloning verifier repo from https://git.openstack.org/openstack/tempest.
    2017-01-18 14:43:32.458 5125 INFO rally.verification.manager [-] Creating virtual environment. It may take a few minutes.
    2017-01-18 14:43:49.786 5125 INFO rally.api [-] Verifier 'tempest-verifier' (UUID=cde1b03d-d1eb-47f2-a997-3fd21b1d8810) has been successfully created!
    Using verifier 'tempest-verifier' (UUID=cde1b03d-d1eb-47f2-a997-3fd21b1d8810) as the default verifier for the future operations.

The command clones Tempest from the
**https://git.openstack.org/openstack/tempest** repository and installs it in
a Python virtual environment for the current deployment by default. All
information about the created verifier is stored in a database. It allows us to
set up different Tempest versions and easily switch between them. How to do it
will be described bellow. You can list all installed verifiers via the
**rally verify list-verifiers** command.

The arguments below allow us to override the default behavior.

Use the **--source** argument to specify an alternate git repository location.
The path to a local Tempest repository or a URL of a remote repository are
both valid values.

.. code-block:: console

    $ rally verify create-verifier --type tempest --name tempest-verifier --source /home/ubuntu/tempest/
    2017-01-18 14:53:19.958 5760 INFO rally.api [-] Creating verifier 'tempest-verifier'.
    2017-01-18 14:53:20.166 5760 INFO rally.verification.manager [-] Cloning verifier repo from /home/ubuntu/tempest/.
    2017-01-18 14:53:20.299 5760 INFO rally.verification.manager [-] Creating virtual environment. It may take a few minutes.
    2017-01-18 14:53:32.517 5760 INFO rally.api [-] Verifier 'tempest-verifier' (UUID=3f878030-1edf-455c-ae5e-07836e3d7e35) has been successfully created!
    Using verifier 'tempest-verifier' (UUID=3f878030-1edf-455c-ae5e-07836e3d7e35) as the default verifier for the future operations.

.. code-block:: console

    $ rally verify create-verifier --type tempest --name tempest-verifier --source https://github.com/openstack/tempest.git
    2017-01-18 14:54:57.786 5907 INFO rally.api [-] Creating verifier 'tempest-verifier'.
    2017-01-18 14:54:57.990 5907 INFO rally.verification.manager [-] Cloning verifier repo from https://github.com/openstack/tempest.git.
    2017-01-18 14:55:05.729 5907 INFO rally.verification.manager [-] Creating virtual environment. It may take a few minutes.
    2017-01-18 14:55:22.943 5907 INFO rally.api [-] Verifier 'tempest-verifier' (UUID=e84a947c-b9d3-434b-853b-176a597902e5) has been successfully created!
    Using verifier 'tempest-verifier' (UUID=e84a947c-b9d3-434b-853b-176a597902e5) as the default verifier for the future operations.

Use the **--version** argument to specify a Tempest commit ID or tag.

.. code-block:: console

    $ rally verify create-verifier --type tempest --name tempest-verifier --version 198e5b4b871c3d09c20afb56dca9637a8cf86ac8
    2017-01-18 14:57:02.274 6068 INFO rally.api [-] Creating verifier 'tempest-verifier'.
    2017-01-18 14:57:02.461 6068 INFO rally.verification.manager [-] Cloning verifier repo from https://git.openstack.org/openstack/tempest.
    2017-01-18 14:57:15.356 6068 INFO rally.verification.manager [-] Switching verifier repo to the '198e5b4b871c3d09c20afb56dca9637a8cf86ac8' version.
    2017-01-18 14:57:15.423 6068 INFO rally.verification.manager [-] Creating virtual environment. It may take a few minutes.
    2017-01-18 14:57:28.004 6068 INFO rally.api [-] Verifier 'tempest-verifier' (UUID=532d7ad2-902e-4764-aa53-335f67dadc7f) has been successfully created!
    Using verifier 'tempest-verifier' (UUID=532d7ad2-902e-4764-aa53-335f67dadc7f) as the default verifier for the future operations.

.. code-block:: console

    $ rally verify create-verifier --type tempest --name tempest-verifier --source /home/ubuntu/tempest/ --version 13.0.0
    2017-01-18 15:01:53.971 6518 INFO rally.api [-] Creating verifier 'tempest-verifier'.
    2017-01-18 15:01:54.180 6518 INFO rally.verification.manager [-] Cloning verifier repo from /home/ubuntu/tempest/.
    2017-01-18 15:01:54.274 6518 INFO rally.verification.manager [-] Switching verifier repo to the '13.0.0' version.
    2017-01-18 15:01:54.336 6518 INFO rally.verification.manager [-] Creating virtual environment. It may take a few minutes.
    2017-01-18 15:02:06.623 6518 INFO rally.api [-] Verifier 'tempest-verifier' (UUID=96ffc4bc-4ac2-4ae9-b3c2-d6b16b871027) has been successfully created!
    Using verifier 'tempest-verifier' (UUID=96ffc4bc-4ac2-4ae9-b3c2-d6b16b871027) as the default verifier for the future operations.

Use the **--system-wide** argument to perform system-wide Tempest installation.
In this case, the virtual environment will not be created and Tempest
requirements will not be installed. Moreover, it is assumed that requirements
are already present in the local environment. This argument is useful when
users don't have an Internet connection to install requirements, but they have
pre-installed ones in the local environment.

.. code-block:: console

    $ rally verify create-verifier --type tempest --name tempest-verifier --source /home/ubuntu/tempest/ --version 13.0.0 --system-wide
    2017-01-18 15:22:09.198 7224 INFO rally.api [-] Creating verifier 'tempest-verifier'.
    2017-01-18 15:22:09.408 7224 INFO rally.verification.manager [-] Cloning verifier repo from /home/ubuntu/tempest/.
    2017-01-18 15:22:09.494 7224 INFO rally.verification.manager [-] Switching verifier repo to the '13.0.0' version.
    2017-01-18 15:22:10.965 7224 INFO rally.api [-] Verifier 'tempest-verifier' (UUID=14c94c12-633a-4522-bd3d-2508f2b9d681) has been successfully created!
    Using verifier 'tempest-verifier' (UUID=14c94c12-633a-4522-bd3d-2508f2b9d681) as the default verifier for the future operations.

To delete the Tempest verifier for all deployments execute the following
command:

.. code-block:: console

    $ rally verify delete-verifier --id 14c94c12-633a-4522-bd3d-2508f2b9d681
    2017-01-18 15:27:03.485 7474 INFO rally.api [-] Deleting verifier 'tempest-verifier' (UUID=14c94c12-633a-4522-bd3d-2508f2b9d681).
    2017-01-18 15:27:03.607 7474 INFO rally.api [-] Verifier has been successfully deleted!

If you have any verifications, use the **--force** argument to delete the
verifier and all stored verifications.

.. code-block:: console

    $ rally verify delete-verifier --id ec58af86-5217-4bbd-b9e5-491df6873b82
    Failed to delete verifier 'tempest-verifier' (UUID=ec58af86-5217-4bbd-b9e5-491df6873b82) because there are stored verifier verifications! Please, make sure that they are not important to you. Use 'force' flag if you would like to delete verifications as well.

.. code-block:: console

    $ rally verify delete-verifier --id ec58af86-5217-4bbd-b9e5-491df6873b82 --force
    2017-01-18 15:49:12.840 8685 INFO rally.api [-] Deleting all verifications created by verifier 'tempest-verifier' (UUID=ec58af86-5217-4bbd-b9e5-491df6873b82).
    2017-01-18 15:49:12.843 8685 INFO rally.api [-] Deleting verification (UUID=c3d1408a-a224-4d31-b38f-4caf8ce06a95).
    2017-01-18 15:49:12.951 8685 INFO rally.api [-] Verification has been successfully deleted!
    2017-01-18 15:49:12.961 8685 INFO rally.api [-] Deleting verification (UUID=a437537e-538b-4637-b6ab-ecb8072f0c71).
    2017-01-18 15:49:13.052 8685 INFO rally.api [-] Verification has been successfully deleted!
    2017-01-18 15:49:13.061 8685 INFO rally.api [-] Deleting verification (UUID=5cec0579-4b4e-46f3-aeb4-a481a7bc5663).
    2017-01-18 15:49:13.152 8685 INFO rally.api [-] Verification has been successfully deleted!
    2017-01-18 15:49:13.152 8685 INFO rally.api [-] Deleting verifier 'tempest-verifier' (UUID=ec58af86-5217-4bbd-b9e5-491df6873b82).
    2017-01-18 15:49:13.270 8685 INFO rally.api [-] Verifier has been successfully deleted!

Use the **--deployment-id** argument to remove the only deployment-specific
data, for example, the config file, etc.

.. code-block:: console

    $ rally verify delete-verifier --deployment-id 351fdfa2-99ad-4447-ba31-22e76630df97
    2017-01-18 15:30:27.793 7659 INFO rally.api [-] Deleting deployment-specific data for verifier 'tempest-verifier' (UUID=ec58af86-5217-4bbd-b9e5-491df6873b82).
    2017-01-18 15:30:27.797 7659 INFO rally.api [-] Deployment-specific data has been successfully deleted!

When the **--deployment-id** and **--force** arguments are used together,
the only deployment-specific data and only verifications of the specified
deployment will be deleted.

.. code-block:: console

    $ rally verify delete-verifier --deployment-id 351fdfa2-99ad-4447-ba31-22e76630df97 --force
    2017-01-18 15:55:02.657 9004 INFO rally.api [-] Deleting all verifications created by verifier 'tempest-verifier' (UUID=fbbd2bc0-dd92-4e1d-805c-672af7c5ec78) for deployment '351fdfa2-99ad-4447-ba31-22e76630df97'.
    2017-01-18 15:55:02.661 9004 INFO rally.api [-] Deleting verification (UUID=a3d3d53c-79a6-4151-85ce-f4a7323d2f4c).
    2017-01-18 15:55:02.767 9004 INFO rally.api [-] Verification has been successfully deleted!
    2017-01-18 15:55:02.776 9004 INFO rally.api [-] Deleting verification (UUID=eddea799-bbc5-485c-a284-1747a30e3f1e).
    2017-01-18 15:55:02.869 9004 INFO rally.api [-] Verification has been successfully deleted!
    2017-01-18 15:55:02.870 9004 INFO rally.api [-] Deleting deployment-specific data for verifier 'tempest-verifier' (UUID=fbbd2bc0-dd92-4e1d-805c-672af7c5ec78).
    2017-01-18 15:55:02.878 9004 INFO rally.api [-] Deployment-specific data has been successfully deleted!


Configure Tempest verifier
--------------------------

Execute the following command to configure the Tempest verifier for the current
deployment:

.. code-block:: console

    $ rally verify configure-verifier
    2017-01-18 16:00:24.495 9377 INFO rally.api [-] Configuring verifier 'tempest-verifier' (UUID=59e8bd5b-55e1-4ab8-b506-a5853c7a92e9) for deployment 'tempest' (UUID=4a62f373-9ce7-47a3-8165-6dc7353f754a).
    2017-01-18 16:00:27.497 9377 INFO rally.api [-] Verifier 'tempest-verifier' (UUID=59e8bd5b-55e1-4ab8-b506-a5853c7a92e9) has been successfully configured for deployment 'tempest' (UUID=4a62f373-9ce7-47a3-8165-6dc7353f754a)!

Use the **--deployment-id** argument to configure the verifier for any
deployment registered in Rally.

.. code-block:: console

    $ rally verify configure-verifier --deployment-id <UUID or name of a deployment>

If you want to reconfigure the Tempest verifier, just add the **--reconfigure**
argument to the command.

.. code-block:: console

    $ rally verify configure-verifier --reconfigure
    2017-01-18 16:08:50.932 9786 INFO rally.api [-] Configuring verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97).
    2017-01-18 16:08:50.933 9786 INFO rally.api [-] Verifier is already configured!
    2017-01-18 16:08:50.933 9786 INFO rally.api [-] Reconfiguring verifier.
    2017-01-18 16:08:52.806 9786 INFO rally.api [-] Verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54) has been successfully configured for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97)!

Moreover, it is possible to extend the default verifier configuration by
providing the **--extend** argument.

.. code-block:: console

    $ cat extra_options.conf
    [some-section-1]
    some-option = some-value

    [some-section-2]
    some-option = some-value

.. code-block:: console

    $ rally verify configure-verifier --extend extra_options.conf
    2017-01-18 16:15:12.248 10029 INFO rally.api [-] Configuring verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97).
    2017-01-18 16:15:12.249 10029 INFO rally.api [-] Verifier is already configured!
    2017-01-18 16:15:12.249 10029 INFO rally.api [-] Adding extra options to verifier configuration.
    2017-01-18 16:15:12.439 10029 INFO rally.api [-] Verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54) has been successfully configured for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97)!

.. code-block:: console

    $ rally verify configure-verifier --extend '{section-1: {option: value}, section-2: {option: value}}'
    2017-01-18 16:18:07.317 10180 INFO rally.api [-] Configuring verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97).
    2017-01-18 16:18:07.317 10180 INFO rally.api [-] Verifier is already configured!
    2017-01-18 16:18:07.317 10180 INFO rally.api [-] Adding extra options to verifier configuration.
    2017-01-18 16:18:07.549 10180 INFO rally.api [-] Verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54) has been successfully configured for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97)!

In order to see the generated Tempest config file use the **--show** argument.

.. code-block:: console

    $ rally verify configure-verifier --show
    2017-01-18 16:19:25.412 10227 INFO rally.api [-] Configuring verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97).
    2017-01-18 16:19:25.412 10227 INFO rally.api [-] Verifier is already configured!

    [DEFAULT]
    debug = True
    log_file = tempest.log
    use_stderr = False

    [auth]
    use_dynamic_credentials = True
    admin_username = admin
    admin_password = admin
    admin_project_name = admin
    admin_domain_name = Default
    ...


Start a verification
--------------------

In order to start a verification execute the following command:

.. code-block:: console

    $ rally verify start
    2017-01-18 16:49:35.367 12162 INFO rally.api [-] Starting verification (UUID=0673ca09-bdb6-4814-a33e-17731559ff33) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97) by verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54).
    2017-01-18 16:49:44.404 12162 INFO tempest-verifier [-] {0} tempest.api.baremetal.admin.test_chassis.TestChassis ... skip: TestChassis skipped as Ironic is not available
    2017-01-18 16:49:44.404 12162 INFO tempest-verifier [-] {0} tempest.api.baremetal.admin.test_drivers.TestDrivers ... skip: TestDrivers skipped as Ironic is not available
    2017-01-18 16:49:44.429 12162 INFO tempest-verifier [-] {3} tempest.api.baremetal.admin.test_ports_negative.TestPortsNegative ... skip: TestPortsNegative skipped as Ironic is not available
    2017-01-18 16:49:44.438 12162 INFO tempest-verifier [-] {2} tempest.api.baremetal.admin.test_nodestates.TestNodeStates ... skip: TestNodeStates skipped as Ironic is not available
    2017-01-18 16:49:44.438 12162 INFO tempest-verifier [-] {2} tempest.api.baremetal.admin.test_ports.TestPorts ... skip: TestPorts skipped as Ironic is not available
    2017-01-18 16:49:44.439 12162 INFO tempest-verifier [-] {1} tempest.api.baremetal.admin.test_api_discovery.TestApiDiscovery ... skip: TestApiDiscovery skipped as Ironic is not available
    2017-01-18 16:49:44.439 12162 INFO tempest-verifier [-] {1} tempest.api.baremetal.admin.test_nodes.TestNodes ... skip: TestNodes skipped as Ironic is not available
    2017-01-18 16:49:47.083 12162 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_availability_zone_negative.AZAdminNegativeTestJSON.test_get_availability_zone_list_detail_with_non_admin_user ... success [1.013s]
    2017-01-18 16:49:47.098 12162 INFO tempest-verifier [-] {1} tempest.api.compute.admin.test_availability_zone.AZAdminV2TestJSON.test_get_availability_zone_list ... success [1.063s]
    2017-01-18 16:49:47.321 12162 INFO tempest-verifier [-] {1} tempest.api.compute.admin.test_availability_zone.AZAdminV2TestJSON.test_get_availability_zone_list_detail ... success [0.224s]
    ...

By default, the command runs the full suite of Tempest tests for the current
deployment. Also, it is possible to run tests of any created verifier, and for
any registered deployment in Rally, using the **--id** and **--deployment-id**
arguments.

.. code-block:: console

    $ rally verify start --id <UUID or name of a verifier> --deployment-id <UUID or name of a deployment>

Also, there is a possibility to run a certain suite of Tempest tests, using
the **--pattern** argument.

.. code-block:: console

    $ rally verify start --pattern set=compute
    2017-01-18 16:58:40.378 12631 INFO rally.api [-] Starting verification (UUID=a4bd3993-ba3d-425c-ab81-38b2f627e682) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97) by verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54).
    2017-01-18 16:58:44.883 12631 INFO tempest-verifier [-] {1} tempest.api.compute.admin.test_auto_allocate_network.AutoAllocateNetworkTest ... skip: The microversion range[2.37 - latest] of this test is out of the configuration range[None - None].
    2017-01-18 16:58:47.330 12631 INFO tempest-verifier [-] {1} tempest.api.compute.admin.test_availability_zone.AZAdminV2TestJSON.test_get_availability_zone_list ... success [0.680s]
    2017-01-18 16:58:47.416 12631 INFO tempest-verifier [-] {2} tempest.api.compute.admin.test_availability_zone_negative.AZAdminNegativeTestJSON.test_get_availability_zone_list_detail_with_non_admin_user ... success [0.761s]
    2017-01-18 16:58:47.610 12631 INFO tempest-verifier [-] {1} tempest.api.compute.admin.test_availability_zone.AZAdminV2TestJSON.test_get_availability_zone_list_detail ... success [0.280s]
    2017-01-18 16:58:47.694 12631 INFO tempest-verifier [-] {3} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_using_string_ram ... success [1.015s]
    2017-01-18 16:58:48.514 12631 INFO tempest-verifier [-] {3} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_verify_entry_in_list_details ... success [0.820s]
    2017-01-18 16:58:48.675 12631 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_create_agent ... success [0.777s]
    2017-01-18 16:58:49.090 12631 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_delete_agent ... success [0.415s]
    2017-01-18 16:58:49.160 12631 INFO tempest-verifier [-] {3} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_int_id ... success [0.646s]
    2017-01-18 16:58:49.546 12631 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_agents.AgentsAdminTestJSON.test_list_agents ... success [0.455s]
    ...

Available suites for Tempest 14.0.0 (the latest Tempest release when this
documentation was written) are **full**, **smoke**, **compute**, **identity**,
**image**, **network**, **object_storage**, **orchestration**, **volume**,
**scenario**. The number of available suites depends on Tempest version because
some test sets move from the Tempest tree to the corresponding Tempest plugins.

Moreover, users can run a certain set of tests, using a regular expression.

.. code-block:: console

    $ rally verify start --pattern tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON
    2017-01-18 17:00:36.590 12745 INFO rally.api [-] Starting verification (UUID=1e12510e-7391-48ed-aba2-8fefe1075a87) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97) by verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54).
    2017-01-18 17:00:44.241 12745 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_using_string_ram ... success [1.044s]
    2017-01-18 17:00:45.108 12745 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_verify_entry_in_list_details ... success [0.868s]
    2017-01-18 17:00:45.863 12745 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_int_id ... success [0.754s]
    2017-01-18 17:00:47.575 12745 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_none_id ... success [1.712s]
    2017-01-18 17:00:48.260 12745 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_uuid_id ... success [0.684s]
    2017-01-18 17:00:50.951 12745 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_list_flavor_without_extra_data ... success [2.689s]
    2017-01-18 17:00:51.631 12745 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_server_with_non_public_flavor ... success [0.680s]
    2017-01-18 17:00:54.192 12745 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_is_public_string_variations ... success [2.558s]
    2017-01-18 17:00:55.102 12745 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_list_non_public_flavor ... success [0.911s]
    2017-01-18 17:00:55.774 12745 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_list_public_flavor_with_other_user ... success [0.673s]
    2017-01-18 17:00:59.602 12745 INFO rally.api [-] Verification (UUID=1e12510e-7391-48ed-aba2-8fefe1075a87) has been successfully finished for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97)!

    ======
    Totals
    ======
    Ran: 10 tests in 14.578 sec.
     - Success: 10
     - Skipped: 0
     - Expected failures: 0
     - Unexpected success: 0
     - Failures: 0

    Using verification (UUID=1e12510e-7391-48ed-aba2-8fefe1075a87) as the default verification for the future operations.

In such a way it is possible to run tests from a certain directory or class,
and even run a single test.

.. code-block:: console

    $ rally verify start --pattern tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_using_string_ram
    2017-01-18 17:01:43.993 12819 INFO rally.api [-] Starting verification (UUID=b9a386e1-d1a1-41b3-b369-9607173de63e) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97) by verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54).
    2017-01-18 17:01:52.592 12819 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_using_string_ram ... success [1.214s]
    2017-01-18 17:01:57.220 12819 INFO rally.api [-] Verification (UUID=b9a386e1-d1a1-41b3-b369-9607173de63e) has been successfully finished for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97)!

    ======
    Totals
    ======
    Ran: 1 tests in 4.139 sec.
     - Success: 1
     - Skipped: 0
     - Expected failures: 0
     - Unexpected success: 0
     - Failures: 0

    Using verification (UUID=b9a386e1-d1a1-41b3-b369-9607173de63e) as the default verification for the future operations.

In order to see errors of failed tests after the verification finished use the
**--detailed** argument.

.. code-block:: console

    $ rally verify start --pattern tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON --detailed
    2017-01-25 19:34:41.113 16123 INFO rally.api [-] Starting verification (UUID=ceb6f26b-5830-42c5-ab09-bfd985ed4cb7) for deployment 'tempest-2' (UUID=38a397d0-ee11-475d-ab08-e17be09d0bcd) by verifier 'tempest-verifier' (UUID=bbf51ada-9dd6-4b25-b1b6-b651e0541dde).
    2017-01-25 19:34:50.188 16123 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az ... fail [0.784s]
    2017-01-25 19:34:51.587 16123 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_get_details ... success [1.401s]
    2017-01-25 19:34:52.947 16123 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_list ... success [1.359s]
    2017-01-25 19:34:53.863 16123 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_remove_host ... success [0.915s]
    2017-01-25 19:34:54.577 16123 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_delete ... success [0.714s]
    2017-01-25 19:34:55.221 16123 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_delete_with_az ... success [0.643s]
    2017-01-25 19:34:55.974 16123 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_update_metadata_get_details ... success [0.752s]
    2017-01-25 19:34:56.689 16123 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_update_with_az ... success [0.714s]
    2017-01-25 19:34:57.144 16123 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_verify_entry_in_list ... success [0.456s]
    2017-01-25 19:35:01.132 16123 INFO rally.api [-] Verification (UUID=ceb6f26b-5830-42c5-ab09-bfd985ed4cb7) has been successfully finished for deployment 'tempest-2' (UUID=38a397d0-ee11-475d-ab08-e17be09d0bcd)!

    =============================
    Failed 1 test - output below:
    =============================

    tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az
    ---------------------------------------------------------------------------------------------------------------
    Traceback (most recent call last):
      File "tempest/api/compute/admin/test_aggregates.py", line 226, in test_aggregate_add_host_create_server_with_az
        self.client.add_host(aggregate['id'], host=self.host)
      File "tempest/lib/services/compute/aggregates_client.py", line 95, in add_host
        post_body)
      File "tempest/lib/common/rest_client.py", line 275, in post
        return self.request('POST', url, extra_headers, headers, body, chunked)
      File "tempest/lib/services/compute/base_compute_client.py", line 48, in request
        method, url, extra_headers, headers, body, chunked)
      File "tempest/lib/common/rest_client.py", line 663, in request
        self._error_checker(resp, resp_body)
      File "tempest/lib/common/rest_client.py", line 775, in _error_checker
        raise exceptions.Conflict(resp_body, resp=resp)
    tempest.lib.exceptions.Conflict: An object with that identifier already exists
    Details: {u'message': u"Cannot add host to aggregate 2658. Reason: One or more hosts already in availability zone(s) [u'tempest-test_az-34611847'].", u'code': 409}

    ======
    Totals
    ======

    Ran: 9 tests in 12.391 sec.
     - Success: 8
     - Skipped: 0
     - Expected failures: 0
     - Unexpected success: 0
     - Failures: 1

    Using verification (UUID=ceb6f26b-5830-42c5-ab09-bfd985ed4cb7) as the default verification for the future operations.

Also, there is a possibility to run Tempest tests from a file. Users can
specify a list of tests in the file and run them, using the **--load-list**
argument.

.. code-block:: console

    $ cat load-list.txt
    tempest.api.identity.admin.v2.test_endpoints.EndPointsTestJSON.test_create_list_delete_endpoint[id-9974530a-aa28-4362-8403-f06db02b26c1]
    tempest.api.identity.admin.v2.test_endpoints.EndPointsTestJSON.test_list_endpoints[id-11f590eb-59d8-4067-8b2b-980c7f387f51]
    tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_assign_user_role[id-0146f675-ffbd-4208-b3a4-60eb628dbc5e]
    tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_get_role_by_id[id-db6870bd-a6ed-43be-a9b1-2f10a5c9994f]
    tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_list_roles[id-75d9593f-50b7-4fcf-bd64-e3fb4a278e23]
    tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_list_user_roles[id-262e1e3e-ed71-4edd-a0e5-d64e83d66d05]
    tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_remove_user_role[id-f0b9292c-d3ba-4082-aa6c-440489beef69]
    tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_role_create_delete[id-c62d909d-6c21-48c0-ae40-0a0760e6db5e]

.. code-block:: console

    $ rally verify start --load-list load-list.txt
    2017-01-18 17:04:13.900 12964 INFO rally.api [-] Starting verification (UUID=af766b2f-cada-44db-a0c2-336ab0c17c27) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97) by verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54).
    2017-01-18 17:04:21.813 12964 INFO tempest-verifier [-] {1} tempest.api.identity.admin.v2.test_endpoints.EndPointsTestJSON.test_create_list_delete_endpoint ... success [1.237s]
    2017-01-18 17:04:22.115 12964 INFO tempest-verifier [-] {1} tempest.api.identity.admin.v2.test_endpoints.EndPointsTestJSON.test_list_endpoints ... success [0.301s]
    2017-01-18 17:04:24.507 12964 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_assign_user_role ... success [3.663s]
    2017-01-18 17:04:25.164 12964 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_get_role_by_id ... success [0.657s]
    2017-01-18 17:04:25.435 12964 INFO tempest-verifier [-] {2} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_list_roles ... success [0.271s]
    2017-01-18 17:04:27.905 12964 INFO tempest-verifier [-] {2} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_list_user_roles ... success [2.468s]
    2017-01-18 17:04:30.645 12964 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_remove_user_role ... success [2.740s]
    2017-01-18 17:04:31.886 12964 INFO tempest-verifier [-] {3} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_role_create_delete ... success [1.239s]
    2017-01-18 17:04:38.122 12964 INFO rally.api [-] Verification (UUID=af766b2f-cada-44db-a0c2-336ab0c17c27) has been successfully finished for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97)!

    ======
    Totals
    ======
    Ran: 8 tests in 14.748 sec.
     - Success: 8
     - Skipped: 0
     - Expected failures: 0
     - Unexpected success: 0
     - Failures: 0

    Using verification (UUID=af766b2f-cada-44db-a0c2-336ab0c17c27) as the default verification for the future operations.

Moreover, it is possible to skip a certain list of Tempest tests, using the
**--skip-list** argument; this should be a yaml file containing key-value
pairs, where the keys are a regex to match against the test name. The values
are the reason why the test was skipped. If an invalid regex is supplied the
key is treated as a test id. For example:

.. code-block:: console

    $ cat skip-list.yaml
    tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_using_string_ram[id-3b541a2e-2ac2-4b42-8b8d-ba6e22fcd4da]:
    tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_verify_entry_in_list_details[id-8261d7b0-be58-43ec-a2e5-300573c3f6c5]: Reason 1
    tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_int_id[id-8b4330e1-12c4-4554-9390-e6639971f086]:
    tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_none_id[id-f83fe669-6758-448a-a85e-32d351f36fe0]: Reason 2
    tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_uuid_id[id-94c9bb4e-2c2a-4f3c-bb1f-5f0daf918e6d]:

    # Example: Skipping several tests with a partial match:
    ^tempest\.api\.compute.servers\.test_attach_interfaces: skip using a regex

The first five keys are invalid regular expressions and are included in the
skip list as is.

.. code-block:: console

    $ rally verify start --pattern tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON --skip-list skip-list.yaml
    2017-01-18 17:13:44.475 13424 INFO rally.api [-] Starting verification (UUID=ec94b397-b546-4f12-82ba-bb17f052c3d0) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97) by verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54).
    2017-01-18 17:13:49.298 13424 INFO tempest-verifier [-] {-} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_int_id ... skip
    2017-01-18 17:13:49.298 13424 INFO tempest-verifier [-] {-} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_none_id ... skip: Reason 2
    2017-01-18 17:13:49.298 13424 INFO tempest-verifier [-] {-} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_using_string_ram ... skip
    2017-01-18 17:13:49.298 13424 INFO tempest-verifier [-] {-} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_with_uuid_id ... skip
    2017-01-18 17:13:49.299 13424 INFO tempest-verifier [-] {-} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_flavor_verify_entry_in_list_details ... skip: Reason 1
    2017-01-18 17:13:54.035 13424 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_list_flavor_without_extra_data ... success [1.889s]
    2017-01-18 17:13:54.765 13424 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_create_server_with_non_public_flavor ... success [0.732s]
    2017-01-18 17:13:57.478 13424 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_is_public_string_variations ... success [2.709s]
    2017-01-18 17:13:58.438 13424 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_list_non_public_flavor ... success [0.962s]
    2017-01-18 17:13:59.180 13424 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_flavors.FlavorsAdminTestJSON.test_list_public_flavor_with_other_user ... success [0.742s]
    2017-01-18 17:14:03.969 13424 INFO rally.api [-] Verification (UUID=ec94b397-b546-4f12-82ba-bb17f052c3d0) has been successfully finished for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97)!

    ======
    Totals
    ======
    Ran: 10 tests in 9.882 sec.
     - Success: 5
     - Skipped: 5
     - Expected failures: 0
     - Unexpected success: 0
     - Failures: 0

    Using verification (UUID=ec94b397-b546-4f12-82ba-bb17f052c3d0) as the default verification for the future operations.

Also, it is possible to specify the path to a file with a list of Tempest tests
that are expected to fail. In this case, the specified tests will have the
**xfail** status instead of **fail**.

.. code-block:: console

    $ cat xfail-list.yaml
    tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az[id-96be03c7-570d-409c-90f8-e4db3c646996]: Some reason why the test fails

.. code-block:: console

    $ rally verify start --pattern tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON --xfail-list xfail-list.yaml
    2017-01-18 17:20:04.064 13720 INFO rally.api [-] Starting verification (UUID=c416b724-0276-4c24-ab60-3ba7078c0a80) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97) by verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54).
    2017-01-18 17:20:17.359 13720 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_create_server_with_az ... xfail [6.328s]: Some reason why the test fails
    2017-01-18 17:20:18.337 13720 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_get_details ... success [0.978s]
    2017-01-18 17:20:19.379 13720 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_host_list ... success [1.042s]
    2017-01-18 17:20:20.213 13720 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_add_remove_host ... success [0.833s]
    2017-01-18 17:20:20.956 13720 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_delete ... success [0.743s]
    2017-01-18 17:20:21.772 13720 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_delete_with_az ... success [0.815s]
    2017-01-18 17:20:22.737 13720 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_update_metadata_get_details ... success [0.964s]
    2017-01-18 17:20:25.061 13720 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_update_with_az ... success [2.323s]
    2017-01-18 17:20:25.595 13720 INFO tempest-verifier [-] {0} tempest.api.compute.admin.test_aggregates.AggregatesAdminTestJSON.test_aggregate_create_verify_entry_in_list ... success [0.533s]
    2017-01-18 17:20:30.142 13720 INFO rally.api [-] Verification (UUID=c416b724-0276-4c24-ab60-3ba7078c0a80) has been successfully finished for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97)!

    ======
    Totals
    ======
    Ran: 9 tests in 17.118 sec.
     - Success: 8
     - Skipped: 0
     - Expected failures: 1
     - Unexpected success: 0
     - Failures: 0

    Using verification (UUID=c416b724-0276-4c24-ab60-3ba7078c0a80) as the default verification for the future operations.

Sometimes users may want to use the specific concurrency for running tests
based on their deployments and available resources. In this case, they can use
the **--concurrency** argument to specify how many processes to use to run
Tempest tests. The default value (0) auto-detects CPU count.

.. code-block:: console

    $ rally verify start --load-list load-list.txt --concurrency 1
    2017-01-18 17:05:38.658 13054 INFO rally.api [-] Starting verification (UUID=cbf5e604-6bc9-47cd-9c8c-5e4c9e9545a0) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97) by verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54).
    2017-01-18 17:05:45.474 13054 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_endpoints.EndPointsTestJSON.test_create_list_delete_endpoint ... success [0.917s]
    2017-01-18 17:05:45.653 13054 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_endpoints.EndPointsTestJSON.test_list_endpoints ... success [0.179s]
    2017-01-18 17:05:55.497 13054 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_assign_user_role ... success [2.673s]
    2017-01-18 17:05:56.237 13054 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_get_role_by_id ... success [0.740s]
    2017-01-18 17:05:56.642 13054 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_list_roles ... success [0.403s]
    2017-01-18 17:06:00.011 13054 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_list_user_roles ... success [3.371s]
    2017-01-18 17:06:02.987 13054 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_remove_user_role ... success [2.973s]
    2017-01-18 17:06:04.927 13054 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_role_create_delete ... success [1.939s]
    2017-01-18 17:06:11.166 13054 INFO rally.api [-] Verification (UUID=cbf5e604-6bc9-47cd-9c8c-5e4c9e9545a0) has been successfully finished for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97)!

    ======
    Totals
    ======
    Ran: 8 tests in 23.043 sec.
     - Success: 8
     - Skipped: 0
     - Expected failures: 0
     - Unexpected success: 0
     - Failures: 0

    Using verification (UUID=cbf5e604-6bc9-47cd-9c8c-5e4c9e9545a0) as the default verification for the future operations.

Also, there is a possibility to rerun tests from any verification. In order
to rerun tests from some verification execute the following command:

.. code-block:: console

    $ rally verify rerun --uuid cbf5e604-6bc9-47cd-9c8c-5e4c9e9545a0
    2017-01-18 17:29:35.692 14127 INFO rally.api [-] Re-running tests from verification (UUID=cbf5e604-6bc9-47cd-9c8c-5e4c9e9545a0) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97).
    2017-01-18 17:29:35.792 14127 INFO rally.api [-] Starting verification (UUID=51aa3275-f028-4f2d-9d63-0db679fdf266) for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97) by verifier 'tempest-verifier' (UUID=16b73e48-09ad-4a54-92eb-2f2708b72c54).
    2017-01-18 17:29:43.980 14127 INFO tempest-verifier [-] {1} tempest.api.identity.admin.v2.test_endpoints.EndPointsTestJSON.test_create_list_delete_endpoint ... success [2.172s]
    2017-01-18 17:29:44.156 14127 INFO tempest-verifier [-] {1} tempest.api.identity.admin.v2.test_endpoints.EndPointsTestJSON.test_list_endpoints ... success [0.177s]
    2017-01-18 17:29:45.333 14127 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_assign_user_role ... success [3.302s]
    2017-01-18 17:29:45.952 14127 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_get_role_by_id ... success [0.619s]
    2017-01-18 17:29:46.219 14127 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_list_roles ... success [0.266s]
    2017-01-18 17:29:48.964 14127 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_list_user_roles ... success [2.744s]
    2017-01-18 17:29:52.543 14127 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_remove_user_role ... success [3.578s]
    2017-01-18 17:29:53.843 14127 INFO tempest-verifier [-] {0} tempest.api.identity.admin.v2.test_roles.RolesTestJSON.test_role_create_delete ... success [1.300s]
    2017-01-18 17:30:01.258 14127 INFO rally.api [-] Verification (UUID=51aa3275-f028-4f2d-9d63-0db679fdf266) has been successfully finished for deployment 'tempest-2' (UUID=351fdfa2-99ad-4447-ba31-22e76630df97)!

    ======
    Totals
    ======
    Ran: 8 tests in 14.926 sec.
     - Success: 8
     - Skipped: 0
     - Expected failures: 0
     - Unexpected success: 0
     - Failures: 0

    Verification UUID: 51aa3275-f028-4f2d-9d63-0db679fdf266.

In order to rerun only failed tests add the **--failed** argument to the
command.

.. code-block:: console

    $ rally verify rerun --uuid <UUID of a verification> --failed

A separated page about building verification reports:
:ref:`verification-reports`.
