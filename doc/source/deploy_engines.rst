..
      Copyright 2014 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _deploy_engines:

Deploy engines
==============


Introduction
------------

One of the core entities in Rally architecture are the Deploy engines. The task of a deploy engine is to control the process of deploying some OpenStack distribution like DevStack or FUEL before any benchmarking procedures take place. Every deploy engine should implement the following fairly simple interface:

..

    **constuctor**, which takes a deployment entity as its only parameter;

..

    **deploy()**, which should deploy the appropriate OpenStack distribution given the cloud config from the deployment object the engine was initialized with (possibly using one of available :ref:`server providers <server_providers>`). The method should also return a dictionary with endpoints of the deployed OpenStack distribution;

..

    **cleanup()**, which should clean up the OpenStack deployment (again, possibly using one of available :ref:`server providers <server_providers>`).


Below you will find a short but informative description of deploy engines implemented in Rally.


Available Deploy engines
------------------------


ExistingCloud
^^^^^^^^^^^^^

**Description**

This engine in fact does not deploy anything, but uses an existing OpenStack installation. It may be useful in case you have a preconfigured OpenStack deployment ready to launch benchmark scenarios.

**Configuration Example**

.. code-block:: none

   {
       "type": "ExistingCloud",
       "auth_url": "http://192.168.122.22:5000/v2.0/",
       "endpoint_type": "public",
       "admin": {
            "username": "admin",
            "password": "password",
            "tenant_name": "admin",
       }
   }

Or using keystone v3 API endpoint:

.. code-block:: none

    {
        "type": "ExistingCloud",
        "auth_url": "http://localhost:5000/v3/",
        "endpoint_type": "public",
        "admin": {
            "username": "engineer1",
            "user_domain_name": "qa",
            "project_name": "qa_admin_project",
            "project_domain_name": "qa",
            "password": "password",
            "region_name": "RegionOne",
        }
    }
..

  *endpoint_type*  option will be used later for selecting access method to the cloud.
  Users can select from "public", "internal", "admin" access methods.



All you should specify in the config is the OpenStack cloud endpoint: the auth_url and also admin credentials, including tenant name. Rally will use the specified admin account to manage temporary non-admin tenants and users exploited while launching benchmark scenarios.


DevstackEngine
^^^^^^^^^^^^^^

**Description**

This engine deploys a Devstack cloud using the given Devstack repository.

**Configuration Example**

.. code-block:: none

   {
       "type": "DevstackEngine",
       "localrc": {
           "ADMIN_PASSWORD": "secret",
           "NOVA_REPO": "git://example.com/nova/",
           ...
       },
       "devstack_repo": "git://example.com/devstack/",
       "type": {
           "name": "${PROVIDER_NAME}",
           ...
       }
   }


The localrc field of the Devstack engine configuration will be used to initialize the Devstack's localrc file. As this deploy engine does not use an existing cloud, it also needs a concrete :ref:`server provider <server_providers>` specification: the type of the used provider *(${PROVIDER_NAME})*, followed by provider-specific fields configuration.


**Note**

More Deploy engines are to come in future releases, namely deploy engines for FUEL, Tripple-O etc. Stay tuned.
