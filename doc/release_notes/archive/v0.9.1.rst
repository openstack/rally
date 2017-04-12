============
Rally v0.9.1
============

Overview
--------

+------------------+-----------------------+
| Release date     |      **4/12/2017**    |
+------------------+-----------------------+

Details
-------

Unfortunately, Rally 0.9.0 contains various bugs. We work hard to fix them,
improve our CI to avoid such issues in future and ready to present a new Rally
release which includes only bug-fixes.

Fixed bugs
~~~~~~~~~~

* [deployment] Credentials is not updated as soon as deployment is recreated.
  Need to call recreate request twice.

  `Launchpad bug-report #1675271
  <https://bugs.launchpad.net/rally/+bug/1675271>`_

* [task] Scenario `IronicNodes.create_and_list_node
  <https://rally.readthedocs.io/en/0.9.1/plugins/plugin_reference.html#ironicnodes-create-and-list-node-scenario>`_
  had a wrong check that list of all nodes contains newly created one.

* [task][cleanup] Do not remove quotas in case of existing users

* [task][cleanup] Various traces of neutron resources

* [core] Keystone v3, authentication error for Rally users if the value of
  project_domain_name of admin user isn't equal "default"

  `Launchpad bug-report #1680837
  <https://bugs.launchpad.net/rally/+bug/1680837>`_

* [task] Scenario `NovaHosts.list_and_get_hosts
  <https://rally.readthedocs.io/en/0.9.1/plugins/plugin_reference.html#novahosts-list-and-get-hosts-scenario>`_
  obtains hostname for all hosts. But it fails in some environments if host is
  not compute.

  `Launchpad bug-report #1675254
  <https://bugs.launchpad.net/rally/+bug/1675254>`_

* [verification] Rally fails to run on systems on which python-virtualenv is
  not installed

  `Launchpad bug-report #1678047
  <https://bugs.launchpad.net/rally/+bug/1678047>`_

* [verification] CLI `rally verify rerun
  <https://rally.readthedocs.io/en/0.9.1/verification/cli_reference.html#rally-verify-rerun>`_
  fails with TypeError due to wring integration with Rally API.

Thanks
~~~~~~

 2 Everybody!
