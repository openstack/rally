===============================
Installing Rally using devstack
===============================

The contrib/devstack/ directory contains the files necessary to integrate Rally with devstack.

To install:

    $ DEVSTACK_DIR=.../path/to/devstack
    $ cp lib/rally ${DEVSTACK_DIR}/lib
    $ cp extras.d/70-rally.sh ${DEVSTACK_DIR}/extras.d

To configure devstack to run rally:

    $ cd ${DEVSTACK_DIR}
    $ echo "enable_service rally" >> localrc

Run devstack as normal:

    $ ./stack.sh
