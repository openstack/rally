============
Rally v0.9.0
============

Overview
--------

+------------------+-----------------------+
| Release date     |      **3/20/2017**    |
+------------------+-----------------------+

Details
-------

Command Line Interface
~~~~~~~~~~~~~~~~~~~~~~

* `rally plugin list` now does not contain hidden plugins.

Task component
~~~~~~~~~~~~~~

* Added check for duplicated keys in task files.

* The order of subtasks (scenarios/workloads) is not ignored any more. You can
  generate whatever you want load or use that feature for up the cloud (put
  small scenario to the start of task to wake up the cloud before the real
  load).

* Information about workload creation is added to HTML-reports.

* Task statuses is changed to be more clear and cover more cases:

 - ``verifying`` is renamed to ``validating``.
 - ``failed`` is divided for 2 statuses - ``validation_failed``, which means
   that task did not pass validation step, and ``crashed``, which means that
   something went wrong in rally engine.

* Our awesome cleanup become more awesome! The filter mechanism is improved to
  discover resources in projects created only by Rally (it works for most of
  resources, except several network-related ). It makes possible to run Rally
  with existing users in real tenants without fear to remove something
  important.


Verification component
~~~~~~~~~~~~~~~~~~~~~~

* Fixed an issue with missed tests while listing all supported tests of
  specified verifier.

* Fixed an issue with displaying the wrong version of verifier in case of
  cloning from the local directory.

* Extend `rally verify rerun
  <http://rally.readthedocs.io/en/0.9.0/verification/cli_reference.html#rally-verify-rerun>`_
  with ``--detailed``, ``--no-use``, ``--tag`` and ``--concurrency`` arguments.

* Add output examples for `JSON
  <http://rally.readthedocs.io/en/0.9.0/verification/reports.html#json>`_ and
  `JUnit-XML
  <http://rally.readthedocs.io/en/0.9.0/verification/reports.html#junit-xml>`_
  reporters.

Plugins
~~~~~~~

**Contexts**

* Extend cinder quotas to support ``backups`` and ``backup_gigabytes``.


**Deployment Engines**:

*Updated* Extend `DevstackEngine
<http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html#devstackengine-engine>`_
with ``enable_plugin`` option.

**OpenStack clients**:

* Extend support for auth urls like ``https://example.com:35357/foo/bar/v3``

* Pass endpoint type to heatclient


**Scenarios**:

* *NEW!!*

 - `CinderVolumeTypes.create_and_delete_encryption_type
   <http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html#cindervolumetypes-create-and-delete-encryption-type-scenario>`_

 - `CinderVolumeTypes.create_and_set_volume_type_keys
   <http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html#cindervolumetypes-create-and-set-volume-type-keys-scenario>`_

 - `KeystoneBasic.create_and_list_roles
   <http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html#keystonebasic-create-and-list-roles-scenario>`_

 - `KeystoneBasic.create_and_update_user
   <http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html#keystonebasic-create-and-update-user-scenario>`_

 - `NovaKeypair.create_and_get_keypair
   <http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html#novakeypair-create-and-get-keypair-scenario>`_

 - `NovaServers.resize_shutoff_server
   <http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html#novaservers-resize-shutoff-server-scenario>`_

 - `VMTasks.dd_load_test
   <http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html#vmtasks-dd-load-test-scenario>`_

* *UPDATED!!*

 - Extend `VMTasks.boot_runcommand_delete
   <http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html#vmtasks-boot-runcommand-delete-scenario>`_
   to display just raw text output of executed command.

* *DELETED*

  Scenario `VMTasks.boot_runcommand_delete_custom_image
  <http://rally.readthedocs.io/en/0.8.0/plugins/plugin_reference.html#vmtasks-boot-runcommand-delete-custom-image-scenario>`_
  is removed since `VMTasks.boot_runcommand_delete
  <http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html#vmtasks-boot-runcommand-delete-scenario>`_
  covers the case of that particular scenario without adding any complexity.

**Validators**:

* Extend ``required_contexts`` validator to support ``at least one of the``
  logic.

* Fix a bunch of JSON schemas which are used for validation of all plugins.

Documentation
~~~~~~~~~~~~~

We totally reworked `Plugins Reference
<http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html>`_ page.
Now it looks more like `Command Line Interface
<http://rally.readthedocs.io/en/0.9.0/cli_reference.html>`_, which means that
you can get links for particular parameter of particular plugin.

Also, you can find expected parameters and their types of all contexts, hooks,
SLAs and so on! Most of them still miss descriptions, but we are working on
adding them.

Fixed bugs
~~~~~~~~~~

* [osclients] Custom auth mechanism was used for zaqarclient instead of unified
  keystonesession, which led to auth errors at some envs.

* [plugins] During running
  `CinderVolumes.create_and_restore_volume_backup
  <http://rally.readthedocs.io/en/0.9.0/plugins/plugin_reference.html#cindervolumes-create-and-restore-volume-backup-scenario>`_
  scenario we had a race problem with backup deleting due to wrong check of
  backup status.

* [plugins][verifications] Jenkins expexts "classname" JUnitXML attribute
  instead of "class_name".

Thanks
~~~~~~

 2 Everybody!
