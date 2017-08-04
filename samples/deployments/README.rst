Rally Deployments
=================

Rally needs to have information about OpenStack Cloud before you actually
can run any tests against it.

You need create a deployment input file and run use command bellow:

.. code-block::

    rally deployment create --file <one_of_files_from_this_dir> --name my_cloud

Below you can find samples of supported configurations.

existing.json
-------------

Register existing OpenStack cluster.

existing-keystone-v3.json
-------------------------

Register existing OpenStack cluster that uses Keystone v3.

existing-with-predefined-users.json
--------------------------------------

If you are using read-only backend in Keystone like LDAP, AD then
you need this sample. If you don't specify "users" rally will use already
existing users that you provide.


existing-with-given-endpoint.json
---------------------------------

Register existing OpenStack cluster, with parameter "endpoint" specified
to explicitly set keystone management_url. Use this parameter if
keystone fails to setup management_url correctly.
For example, this parameter must be specified for FUEL cluster
and has value "http://<identity-public-url-ip>:35357/v2.0/"
