============
Rally v0.1.1
============

Information
-----------

+------------------+-----------------------+
| Commits          |         **32**        |
+------------------+-----------------------+
| Bug fixes        |         **9**         |
+------------------+-----------------------+
| Dev cycle        |       **11 days**     |
+------------------+-----------------------+
| Release date     |  **6/October/2015**   |
+------------------+-----------------------+


Details
-------

This release contains new features, new 6 plugins, 9 bug fixes,
various code and API improvements.


New Features
~~~~~~~~~~~~

* **Rally verify generates proper tempest.conf file now**

  Improved script that generates tempest.conf, now it works out of box for
  most of the clouds and most of Tempest tests will pass without hacking it.

* **Import Tempest results to Rally DB**

  ``rally verify import`` command allows you to import already existing Tempest
  results and work with them as regular "rally verify start" results:
  generate HTML/CSV reports & compare different runs.


API Changes
~~~~~~~~~~~~

**Rally CLI changes**

  * [add] ``rally verify import`` imports raw Tempest results to Rally


Specs & Feature requests
~~~~~~~~~~~~~~~~~~~~~~~~

  There is no new specs and feature requests.

Plugins
~~~~~~~

* **Scenarios**:

  [new] NeutronNetworks.create_and_list_floating_ips

  [new] NeutronNetworks.create_and_delete_floating_ips

  [new] MuranoPackages.import_and_list_packages

  [new] MuranoPackages.import_and_delete_package

  [new] MuranoPackages.import_and_filter_applications

  [new] MuranoPackages.package_lifecycle

  [improved] NovaKeypair.boot_and_delete_server_with_keypair

    New argument ``server_kwargs``, these kwargs are used to boot server.

  [fix] NeutronLoadbalancerV1.create_and_delete_vips

      Now it works in case of concurrency > 1


* **Contexts**:

  [improved] network

      Network context accepts two new arguments:
      ``subnets_per_network`` and ``network_create_args``.

  [fix] network

      Fix cleanup if nova-network is used. Networks should be dissociate from
      project before deletion

  [fix] custom_image

      Nova server that is used to create custom image was not deleted if
      script that prepares server failed.


Bug fixes
~~~~~~~~~

**9 bugs were fixed, the most critical are**:

* Fix install_rally.sh script

  Set 777 access to /var/lib/rally/database file if system-wide method of
  installation is used.

* Rally HTML reports Overview table had few mistakes

    * Success rate was always 100%

    * Percentiles were wrongly calculated

* Missing Ironic, Murano and Workload(vm) options in default config file

* ``rally verify start`` failed while getting network_id

* ``rally verify genconfig`` hangs forever if Horizon is not available


Documentation
~~~~~~~~~~~~~

* **Fix project maintainers page**

  Update the information about Rally maintainers

* **Document rally --plugin-paths CLI argument**

* **Code blocks in documentation looks prettier now**

