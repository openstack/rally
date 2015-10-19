===============================
Installing Rally using devstack
===============================

This directory contains the files necessary to integrate Rally with devstack.

To configure devstack to run rally edit ``${DEVSTACK_DIR}/local.conf`` file and add::

    enable_plugin rally https://github.com/openstack/rally master

to the ``[[local|localrc]]`` section.

Run devstack as normal::

    $ ./stack.sh
