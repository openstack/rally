Rally Deployments
=================

Rally needs to be configured to use an OpenStack Cloud deployment before it
can benchmark the deployment.

To configure Rally to use an OpenStack Cloud deployment, you need create a
deployment configuration by supplying the endpoint and credentials, as follows:

.. code-block::

    rally deployment create --file <one_of_files_from_this_dir> --name my_cloud


If you don't have OpenStack deployments, Rally can deploy it for you.
For samples of various deployments take a look at samples from
**for_deploying_openstack_with_rally** directory.


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
