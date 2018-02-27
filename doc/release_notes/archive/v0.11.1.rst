=============
Rally v0.11.1
=============

Overview
--------

+------------------+-----------------------+
| Release date     |     **02/27/2018**    |
+------------------+-----------------------+

* Fix database migration
* Un-cup kubernetes client version in requirements
* Add support for sTestr for verifiers
* Add several new scenarios for Gnocchi

Details
-------

DataBase
~~~~~~~~

Rally <0.10.0 was hardcoded to support only OpenStack platform. That is
why deployment config had a flat schema (i.e openstack credentials were
at the same top-level as other properties).

Rally 0.10 includes an attempt to unify deployment component for
supporting multiple platforms. The deployment config was extended with a
new top level property ``creds`` which was designed to include credentials
for different platforms.
Since Task and Verification components used deployment.credentials object
from database instead of using deployment config directly, Rally 0.10 did
not provide a database migration of deployment config.

While developing Rally 0.11.0 with new Environment component, we made a
wrong assumption and forgot about an old format. That is why a
7287df262dbc migration relied on "creds" property of deployment.config

If the database was created before Rally<0.10, the introduced assumption
leads to KeyError failure[0] for old deployment configuration:

  .. code-block:: console

      File ".../7287df262dbc_move_deployment_to_env.py", line 137, in upgrade
           and (set(spec["creds"]) == {"openstack"}
      KeyError: 'creds'

We fixed this issue and you should easily migrate from Rally < 0.11.0 to
Rally 0.11.1 without any issues.

Verification component
~~~~~~~~~~~~~~~~~~~~~~

OpenStack Tempest team made a decision to switch from `testrepository
<https://testrepository.readthedocs.org/en/latest>`_ test runner to `stestr
<https://github.com/mtreinish/stestr>`_ which is fork of testrepository.

Despite the fact that stestr is not 100% backwards compatible with
testrepository, it is not a hard task to make `Tempest verifier
<https://rally.readthedocs.io/en/0.11.1/verification/verifiers.html#tempest>`_
work with both of them (to support new releases of tempest tool as like
old ones) and it is what we did in Rally 0.11.1

Plugins
~~~~~~~


**Scenarios**:

* *NEW!!*

 `GnocchiArchivePolicyRule.list_archive_policy_rule
 <https://rally.readthedocs.io/en/0.11.1/plugins/plugin_reference.html#gnocchiarchivepolicyrule-list-archive-policy-rule-scenario>`_
 `GnocchiArchivePolicyRule.create_archive_policy_rule
 <https://rally.readthedocs.io/en/0.11.1/plugins/plugin_reference.html#gnocchiarchivepolicyrule-create-archive-policy-rule-scenario>`_
 `GnocchiArchivePolicyRule.create_delete_archive_policy_rule
 <https://rally.readthedocs.io/en/0.11.1/plugins/plugin_reference.html#gnocchiarchivepolicyrule-create-delete-archive-policy-rule-scenario>`_

Thanks
~~~~~~

 2 Everybody!
