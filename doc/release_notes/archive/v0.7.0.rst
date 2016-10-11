============
Rally v0.7.0
============

Overview
--------

+------------------+-----------------------+
| Release date     |     **10/11/2016**    |
+------------------+-----------------------+

Details
-------

Specs & Feature Requests
~~~~~~~~~~~~~~~~~~~~~~~~

* [Used] Ported all rally scenarios to class base

  `Spec reference <https://github.com/openstack/rally/blob/0.7.0/doc/specs/implemented/class-based-scenarios.rst>`_

* `[Implemented] New Plugins Type - Hook <https://github.com/openstack/rally/blob/0.7.0/doc/specs/implemented/hook_plugins.rst>`_

Database
~~~~~~~~

.. warning:: Database schema is changed, you must run
     `rally-manage db upgrade <http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-manage-db-upgrade>`_
     to be able to use old Rally installation with latest release.

* [require migration] fix for wrong format of "verification_log" of tasks
* [require migration] remove admin_domain_name from OpenStack deployments

Rally Deployment
~~~~~~~~~~~~~~~~

* Remove admin_domain_name from openstack deployment
  Reason: admin_domain_name parameter is absent in Keystone Credentials.


Rally Task
~~~~~~~~~~

* [Trends][Reports] Use timestamps on X axis in trends report

* [Reports] Add new OutputTextArea chart plugin

  New chart plugin can show arbitrary textual data on
  "Scenario Stata -> Per iteration" tab.

  This finally allows to show non-numeric data like IP addresses, notes and
  even long comments.

  Plugin `Dummy.dummy_output <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#dummy-dummy-output-scenario>`_
  is also updated to provide demonstration.

* [cli] Add version info to *rally task start* output

* [api] Allow to delete stopped tasks without force=True

  It is reasonable to protect deletion of running tasks (statuses INIT,
  VERIFYING, RUNNING, ABORTING and so on...) but it is strange to protect
  deletion for stopped tasks (statuses FAILED and ABORTED). Also this is
  annoying in CLI usage.

* Added hooks and triggers.

  Hook is a new entity which can be launched on specific events. Trigger is
  another new entity which processes events and launches hooks.
  For example, hook can launch specific destructive action - just execute cli
  command(we have sys_call hook for this task) and it can be launched by
  simple trigger on specific iteration(s) or time (there is event trigger).

Rally Verify
~~~~~~~~~~~~

Scenario tests in Tempest require an image file. Logic of obtaining this image
is changed:

* If CONF.tempest.img_name_regex is set, Rally tries to find an image matching
  to the regex in Glance and download it for the tests.
* If CONF.tempest.img_name_regex is not set (or Rally didn't find the image
  matching to CONF.tempest.img_name_regex), Rally downloads the image by the
  link specified in CONF.tempest.img_url.

Plugins
~~~~~~~

**Scenarios**:

* *Removed*: `Dummy.dummy_with_scenario_output <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#dummy-dummy-with-scenario-output-scenario>`_

  It was deprecated in 0.5.0

  .. warning:: This plugin is not available anymore in 0.7.0

* *NEW!!*:
 - `MagnumClusterTemplates.list_cluster_templates <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#magnumclustertemplates-list-cluster-templates-scenario>`_
 - `MagnumClusters.list_clusters <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#magnumclusters-list-clusters-scenario>`_
 - `MagnumClusters.create_and_list_clusters <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#magnumclusters-create-and-list-clusters-scenario>`_
 - `NovaAggregates.create_aggregate_add_and_remove_host <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#novaaggregates-create-aggregate-add-and-remove-host-scenario>`_
 - `NovaAggregates.create_and_list_aggregates <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#novaaggregates-create-and-list-aggregates-scenario>`_
 - `NovaAggregates.create_and_delete_aggregate <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#novaaggregates-create-and-delete-aggregate-scenario>`_
 - `NovaAggregates.create_and_update_aggregate <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#novaaggregates-create-and-update-aggregate-scenario>`_
 - `NovaFlavors.create_and_get_flavor <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#novaflavors-create-and-get-flavor-scenario>`_
 - `NovaFlavors.create_flavor_and_set_keys <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#novaflavors-create-flavor-and-set-keys-scenario>`_
 - `NovaHypervisors.list_and_get_hypervisors <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#novahypervisors-list-and-get-hypervisors-scenario>`_
 - `NovaServers.boot_server_associate_and_dissociate_floating_ip <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#novaservers-boot-server-associate-and-dissociate-floating-ip-scenario>`_
 - `KeystoneBasic.authenticate_user_and_validate_token <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#keystonebasic-authenticate-user-and-validate-token-scenario>`_

**Contexts**:

* *NEW!!*:
 - `Manila manila_security_services <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#manila-security-services-context>`_
 - `Magnum cluster_templates <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#cluster-templates-context>`_
 - `Magnum clusters <http://rally.readthedocs.io/en/0.7.0/plugin/plugin_reference.html#clusters-context>`_

**OSClients**:

Port all openstack clients to use keystone session.

Bug fixes
~~~~~~~~~

* [tasks] rally task detailed incorrect / inconsistent output

  `Launchpad bug-report #1562713 <https://bugs.launchpad.net/rally/+bug/1562713>`_


Thanks
~~~~~~

 2 Everybody!
