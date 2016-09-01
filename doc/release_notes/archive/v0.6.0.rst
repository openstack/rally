============
Rally v0.6.0
============

Overview
--------

+------------------+-----------------------+
| Release date     |     **9/05/2016**     |
+------------------+-----------------------+

Details
-------

Common
~~~~~~

* Added Python 3.5 support
* Sync requirements with OpenStack global-requirements
* Start using latest way of authentication - keystoneauth library
* Start porting all scenario plugins to class-based view.

Specs & Feature Requests
~~~~~~~~~~~~~~~~~~~~~~~~

* `[Implemented] SLA Performance degradation plugin <https://github.com/openstack/rally/blob/0.6.0/doc/specs/implemented/sla_pd_plugin.rst>`_
* `[Proposed] New Tasks Configuration section - hook <https://github.com/openstack/rally/blob/0.6.0/doc/specs/in-progress/hook_section.rst>`_

Database
~~~~~~~~

* disable db downgrade api
* [require migration] upgrade deployment config

Docker image
~~~~~~~~~~~~

* Add sudo rights to rally user
  Rally is a pluggable framework. External plugins can require installation of
  additional python or system packages, so we decided to add sudo rights.

* Move from ubuntu:14.04 base image to ubuntu:16.04 .
  Ubuntu 16.04 is current/latest LTS release. Let's use it.

* pre-install vim
  Since there are a lot of users who like to experiment and modify samples
  inside container, rally team decided to pre-install vim

* configure/pre-install bash-completion
  Rally provides bash-completion script, but it doesn't work without installed
  `bash-completion` package and now it is included in our image.


Rally Deployment
~~~~~~~~~~~~~~~~

* Add strict jsonschema validation for ExistingCloud deployments. All incorrect
  and unexpected properties will not be ignored anymore. If you need to store
  some extra parameters, you can use new "extra" property.
* Fix an issue with endpoint_type.
  Previously, endpoint type was not transmitted to keystone client. In this
  case, keystoneclient used default endpoint type (for different API calls it
  can differ). Behaviour after the fix:

   - None endpoint type -> Rally will initialize all clients without setting
     endpoint type. It means that clients will choose what default values for
     endpoint type use by itself. Most of clients have "public" as default
     values. Keystone use "admin" or "internal" by default.
   - Not none endpoint type -> Rally will initialize all clients with this
     endpoint. Be careful, by default most of keystone v2 api calls do not work
     with public endpoint type.


Rally Task
~~~~~~~~~~

* [core] Iterations numbers in logging and reports must be synchronized. Now
  they start from 1 .

* [config] users_context.keystone_default_role is a new config option
  (Defaults to "member") for setting default user role for new users in case
  of Keystone V3.

* [Reports] Embed Rally version into HTML reports
  This adds Rally version via meta tag into HTML reports:

    <meta name="generator" content="Rally version {{ version }}">

* [Reports] Expand menu if there is only one menu group

* [logging] Remove deprecated rally.common.log module

* [Trends][Reports] Add success rate chart to trends report

* [Reports] Hide menu list if there is no data at all

Rally Verify
~~~~~~~~~~~~

* Updating Tempest config file
 - Some tests (for boto, horizon, etc.) were removed from Tempest and now there
   is no need to keep the corresponding  options in Tempest config file.

 - Some options in Tempest were moved from one section to another and we should
   to do the corresponding changes in Rally to be up to date with the latest
   Tempest version.

* Adding '--skip-list' arg to `rally verify start` cmd

  `CLI argument for --skip-list <http://rally.readthedocs.io/en/0.6.0/cli/cli_reference.html#verify-start-skiplist>`_

* *NEW!!*:

 - `Command for plugin listing <http://rally.readthedocs.io/en/0.6.0/cli/cli_reference.html#rally-verify-listplugins>`_
 - `Command to uninstall plugins <http://rally.readthedocs.io/en/0.6.0/cli/cli_reference.html#rally-verify-uninstallplugin>`_

* Rename and deprecated several arguments for `rally verify start` cmd:

 - tests-file  -> load-list
 - xfails-file -> xfail-list

Plugins
~~~~~~~

**Scenarios**:

* Extend Sahara scenarios with autoconfig param

  Affected plugins:

 - `SaharaClusters.create_and_delete_cluster <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#saharaclusters-create-and-delete-cluster-scenario>`_
 - `SaharaClusters.create_scale_delete_cluster <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#saharaclusters-create-scale-delete-cluster-scenario>`_
 - `SaharaNodeGroupTemplates.create_and_list_node_group_templates <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#saharanodegrouptemplates-create-and-list-node-group-templates-scenario>`_
 - `SaharaNodeGroupTemplates.create_delete_node_group_templates <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#saharanodegrouptemplates-create-delete-node-group-templates-scenario>`_

* *NEW!!*:
 - `MonascaMetrics.list_metrics <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#monascametrics-list-metrics-scenario>`_
 - `SenlinClusters.create_and_delete_cluster <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#senlinclusters-create-and-delete-cluster-scenario>`_
 - `Watcher.create_audit_template_and_delete <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#watcher-create-audit-template-and-delete-scenario>`_
 - `Watcher.create_audit_and_delete <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#watcher-create-audit-and-delete-scenario>`_
 - `Watcher.list_audit_templates <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#watcher-list-audit-templates-scenario>`_

* Rename **murano.create_service** to **murano.create_services** atomic action

**SLA**:

*NEW!!*: `performance degradation plugin <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#performance-degradation-sla>`_

**Contexts**:

* *NEW!!*:
 - `Monasca monasca_metrics <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#monasca-metrics-context>`_
 - `Senlin profiles <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#profiles-context>`_
 - `Watcher audit_templates <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#audit-templates-context>`_

* Extend `manila_share_networks <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#manila-share-networks-context>`_
  context with share-network autocreation support.

* Extend `volumes <http://rally.readthedocs.io/en/0.6.0/plugin/plugin_reference.html#volumes-context>`_
  context to allow volume_type to be None to allow using default value

Bug fixes
~~~~~~~~~

* [existing users]  Quota context does not restore original settings on exit

  `Launchpad bug-report #1595578 <https://bugs.launchpad.net/rally/+bug/1595578>`_

* [keystone v3] Rally task's test user role setting failed

  `Launchpad bug-report #1595081 <https://bugs.launchpad.net/rally/+bug/1595081>`_

* [existing users] context cannot fetch 'tenant' and 'user' details from cloud
  deployment

  `Launchpad bug-report #1602157 <https://bugs.launchpad.net/rally/+bug/1602157>`_

* UnboundLocalError: local variable 'cmd' referenced before assignment

  `Launchpad bug-report #1587941 <https://bugs.launchpad.net/rally/+bug/1587941>`_

* [Reports] Fix trends report generation if there are n/a results


Documentation
~~~~~~~~~~~~~

* Add page about task reports

  `RTD page for reports <http://rally.readthedocs.io/en/0.6.0/reports.html>`_

Thanks
~~~~~~

 2 Everybody!
