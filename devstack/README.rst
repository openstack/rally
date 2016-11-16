Rally with DevStack all-in-one installation
-------------------------------------------

It is also possible to install Rally with DevStack. First, clone the
corresponding repositories:

.. code-block:: bash

   git clone https://git.openstack.org/openstack-dev/devstack
   git clone https://github.com/openstack/rally

Then, configure DevStack to run Rally. First, create your ``local.conf`` file:

.. code-block:: bash

   cd devstack
   cp samples/local.conf local.conf

Next, edit local.conf: add the following line to the ``[[local|localrc]]``
section.

.. code-block:: bash

    enable_plugin rally https://github.com/openstack/rally master

Finally, run DevStack as usually:

.. code-block:: bash

   ./stack.sh
