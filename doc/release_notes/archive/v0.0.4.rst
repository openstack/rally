============
Rally v0.0.4
============

Information
-----------

+------------------+-----------------+
| Commits          |     **87**      |
+------------------+-----------------+
| Bug fixes        |     **21**      |
+------------------+-----------------+
| Dev cycle        |   **30 days**   |
+------------------+-----------------+
| Release date     | **14/May/2015** |
+------------------+-----------------+


Details
-------

This release contains new features, new benchmark plugins, bug fixes, various code and API improvements.


New Features & API changes
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Rally now can generate load with users that already exist

  Now one can use Rally for benchmarking OpenStack clouds that are using LDAP, AD or any other read-only keystone backend where it is not possible to create any users. To do this, one should set up the "users" section of the deployment configuration of the ExistingCloud type. This feature also makes it safer to run Rally against production clouds: when run from an isolated group of users, Rally won’t affect rest of the cloud users if something goes wrong.

* New decorator *@osclients.Clients.register* can add new OpenStack clients at runtime

  It is now possible to add a new OpenStack client dynamically at runtime. The added client will be available from osclients.Clients at the module level and cached. Example:

.. code-block:: none

   >>> from rally import osclients
   >>> @osclients.Clients.register("supernova")
   ... def another_nova_client(self):
   ...   from novaclient import client as nova
   ...   return nova.Client("2", auth_token=self.keystone().auth_token,
   ...                      **self._get_auth_info(password_key="key"))
   ...
   >>> clients = osclients.Clients.create_from_env()
   >>> clients.supernova().services.list()[:2]
   [<Service: nova-conductor>, <Service: nova-cert>]

* Assert methods now available for scenarios and contexts

  There is now a new *FunctionalMixin* class that implements basic unittest assert methods. The *base.Context* and *base.Scenario* classes inherit from this mixin, so now it is possible to use *base.assertX()* methods in scenarios and contexts.

* Improved installation script

  The installation script has been almost completely rewritten. After this change, it can be run from an unprivileged user, supports different database types, allows to specify a custom python binary, always asks confirmation before doing potentially dangerous actions, automatically install needed software if run as root, and also automatically cleans up the virtualenv and/or the downloaded repository if interrupted.


Specs & Feature requests
~~~~~~~~~~~~~~~~~~~~~~~~

* [Spec] Reorder plugins

  The spec describes how to split Rally framework and plugins codebase to make it simpler for newbies to understand how Rally code is organized and how it works.

* [Feature request] Specify what benchmarks to execute in task

  This feature request proposes to add the ability to specify benchmark(s) to be executed when the user runs the *rally task start* command. A possible solution would be to add a special flag to the *rally task start* command.


Plugins
~~~~~~~

* **Benchmark Scenario Runners**:

    * Add limits for maximum Core usage to constant and rps runners

      The new 'max_cpu_usage' parameter can be used to avoid possible 100% usage of all available CPU cores by reducing the number of CPU cores available for processes started by the corresponding runner.


* **Benchmark Scenarios**:

    * [new] KeystoneBasic.create_update_and_delete_tenant

    * [new] KeystoneBasic.create_user_update_password

    * [new] NovaServers.shelve_and_unshelve_server

    * [new] NovaServers.boot_and_associate_floating_ip

    * [new] NovaServers.boot_lock_unlock_and_delete

    * [new] NovaHypervisors.list_hypervisors

    * [new] CeilometerSamples.list_samples

    * [new] CeilometerResource.get_resources_on_tenant

    * [new] SwiftObjects.create_container_and_object_then_delete_all

    * [new] SwiftObjects.create_container_and_object_then_download_object

    * [new] SwiftObjects.create_container_and_object_then_list_objects

    * [new] MuranoEnvironments.create_and_deploy_environment

    * [new] HttpRequests.check_random_request

    * [new] HttpRequests.check_request

    * [improved] NovaServers live migrate benchmarks

        add 'min_sleep' and 'max_sleep' parameters to simulate a pause between VM booting and running live migration

    * [improved] NovaServers.boot_and_live_migrate_server

        add a usage sample to samples/tasks

    * [improved] CinderVolumes benchmarks

        support size range to be passed to the 'size' argument as a dictionary
        *{"min": <minimum_size>, "max": <maximum_size>}*


* **Benchmark Contexts**:

    * [new] MuranoPackage

      This new context can upload a package to Murano from some specified path.

    * [new] CeilometerSampleGenerator

      Context that can be used for creating samples and collecting resources for benchmarks in a list.


* **Benchmark SLA**:

    * [new] outliers

      This new SLA checks that the number of outliers (calculated from the mean and standard deviation of the iteration durations) does not exceed some maximum value. The SLA is highly configurable: the parameters used for outliers threshold calculation can be set by the user.


Bug fixes
~~~~~~~~~

**21 bugs were fixed, the most critical are**:

* Make it possible to use relative imports for plugins that are outside of rally package.

* Fix heat stacks cleanup by deleting them only 1 time per tenant (get rid of "stack not found" errors in logs).

* Fix the wrong behavior of 'rally task detailed --iterations-data' (it lacked the iteration info before).

* Fix security groups cleanup: a security group called "default", created automatically by Neutron, did not get deleted for each tenant.


Other changes
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Streaming algorithms that scale

  This release introduces the common/streaming_algorithms.py module. This module is going to contain implementations of benchmark data processing algorithms that scale: these algorithms do not store exhaustive information about every single benchmark iteration duration processed. For now, the module contains implementations of algorithms for computation of mean & standard deviation.

* Coverage job to check that new patches come with unit tests

  Rally now has a coverage job that checks that every patch submitted for review does not decrease the number of lines covered by unit tests (at least too much). This job allows to mark most patches with no unit tests with '-1'.

* Splitting the plugins code (Runners & SLA) into common/openstack plugins

  According to the spec "Reorder plugins" (see above), the plugins code for runners and SLA has been moved to the *plugins/common/* directory. Only base classes now remain in the *benchmark/* directory.


Documentation
~~~~~~~~~~~~~

* Various fixes

    * Remove obsolete *.rst* files (*deploy_engines.rst* / *server_providers.rst* / ...)
    * Restructure the docs files to make them easier to navigate through
    * Move the chapter on task templates to the 4th step in the tutorial
    * Update the information about meetings (new release meeting & time changes)
