===============================
Installing Rally using devstack
===============================

This directory contains the files necessary to integrate Rally with devstack.

To configure devstack to run rally::

    $ cd ${DEVSTACK_DIR}
    $ echo "enable_plugin rally https://github.com/openstack/rally master" >> localrc

Run devstack as normal::

    $ ./stack.sh
