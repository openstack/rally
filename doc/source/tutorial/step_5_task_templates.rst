..
      Copyright 2015 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _tutorial_step_5_task_templates:

Step 5. Rally task templates
============================

.. contents::
   :local:

Basic template syntax
---------------------

A nice feature of the input task format used in Rally is that it supports the **template syntax** based on `Jinja2 <https://pypi.python.org/pypi/Jinja2>`_. This turns out to be extremely useful when, say, you have a fixed structure of your task but you want to parameterize this task in some way. For example, imagine your input task file (*task.yaml*) runs a set of Nova scenarios:

.. code-block:: yaml

    ---
      NovaServers.boot_and_delete_server:
        -
          args:
            flavor:
                name: "m1.tiny"
            image:
                name: "^cirros.*uec$"
          runner:
            type: "constant"
            times: 2
            concurrency: 1
          context:
            users:
              tenants: 1
              users_per_tenant: 1

      NovaServers.resize_server:
        -
          args:
            flavor:
                name: "m1.tiny"
            image:
                name: "^cirros.*uec$"
            to_flavor:
                name: "m1.small"
          runner:
            type: "constant"
            times: 3
            concurrency: 1
          context:
            users:
              tenants: 1
              users_per_tenant: 1

In both scenarios above, the *"^cirros.*uec$"* image is passed to the scenario as an argument (so that these scenarios use an appropriate image while booting servers). Let’s say you want to run the same set of scenarios with the same runner/context/sla, but you want to try another image while booting server to compare the performance. The most elegant solution is then to turn the image name into a template variable:

.. code-block:: yaml

    ---
      NovaServers.boot_and_delete_server:
        -
          args:
            flavor:
                name: "m1.tiny"
            image:
                name: {{image_name}}
          runner:
            type: "constant"
            times: 2
            concurrency: 1
          context:
            users:
              tenants: 1
              users_per_tenant: 1

      NovaServers.resize_server:
        -
          args:
            flavor:
                name: "m1.tiny"
            image:
                name: {{image_name}}
            to_flavor:
                name: "m1.small"
          runner:
            type: "constant"
            times: 3
            concurrency: 1
          context:
            users:
              tenants: 1
              users_per_tenant: 1

and then pass the argument value for **{{image_name}}** when starting a task with this configuration file. Rally provides you with different ways to do that:


1. Pass the argument values directly in the command-line interface (with either a JSON or YAML dictionary):

.. code-block:: bash

    rally task start task.yaml --task-args '{"image_name": "^cirros.*uec$"}'
    rally task start task.yaml --task-args 'image_name: "^cirros.*uec$"'

2. Refer to a file that specifies the argument values (JSON/YAML):

.. code-block:: bash

    rally task start task.yaml --task-args-file args.json
    rally task start task.yaml --task-args-file args.yaml

where the files containing argument values should look as follows:

*args.json*:

.. code-block:: json

    {
        "image_name": "^cirros.*uec$"
    }

*args.yaml*:

.. code-block:: yaml

    ---
      image_name: "^cirros.*uec$"

Passed in either way, these parameter values will be substituted by Rally when starting a task:

.. code-block:: console

    $ rally task start task.yaml --task-args "image_name: "^cirros.*uec$""
    --------------------------------------------------------------------------------
     Preparing input task
    --------------------------------------------------------------------------------

    Input task is:
    ---

      NovaServers.boot_and_delete_server:
        -
          args:
            flavor:
                name: "m1.tiny"
            image:
                name: ^cirros.*uec$
          runner:
            type: "constant"
            times: 2
            concurrency: 1
          context:
            users:
              tenants: 1
              users_per_tenant: 1

      NovaServers.resize_server:
        -
          args:
            flavor:
                name: "m1.tiny"
            image:
                name: ^cirros.*uec$
            to_flavor:
                name: "m1.small"
          runner:
            type: "constant"
            times: 3
            concurrency: 1
          context:
            users:
              tenants: 1
              users_per_tenant: 1

    --------------------------------------------------------------------------------
     Task  cbf7eb97-0f1d-42d3-a1f1-3cc6f45ce23f: started
    --------------------------------------------------------------------------------

    Benchmarking... This can take a while...


Using the default values
------------------------

Note that the Jinja2 template syntax allows you to set the default values for your parameters. With default values set, your task file will work even if you don't parameterize it explicitly while starting a task. The default values should be set using the *{% set ... %}* clause (*task.yaml*):

.. code-block:: yaml

    {% set image_name = image_name or "^cirros.*uec$" %}
    ---

      NovaServers.boot_and_delete_server:
        -
          args:
            flavor:
                name: "m1.tiny"
            image:
                name: {{image_name}}
          runner:
            type: "constant"
            times: 2
            concurrency: 1
          context:
            users:
              tenants: 1
              users_per_tenant: 1

        ...

If you don't pass the value for *{{image_name}}* while starting a task, the default one will be used:

.. code-block:: console

    $ rally task start task.yaml
    --------------------------------------------------------------------------------
     Preparing input task
    --------------------------------------------------------------------------------

    Input task is:
    ---

      NovaServers.boot_and_delete_server:
        -
          args:
            flavor:
                name: "m1.tiny"
            image:
                name: ^cirros.*uec$
          runner:
            type: "constant"
            times: 2
            concurrency: 1
          context:
            users:
              tenants: 1
              users_per_tenant: 1

        ...


Advanced templates
------------------

Rally makes it possible to use all the power of Jinja2 template syntax, including the mechanism of **built-in functions**. This enables you to construct elegant task files capable of generating complex load on your cloud.

As an example, let us make up a task file that will create new users with increasing concurrency. The input task file (*task.yaml*) below uses the Jinja2 **for-endfor** construct to accomplish that:


.. code-block:: yaml

    ---
      KeystoneBasic.create_user:
      {% for i in range(2, 11, 2) %}
        -
          args: {}
          runner:
            type: "constant"
            times: 10
            concurrency: {{i}}
          sla:
            failure_rate:
              max: 0
      {% endfor %}


In this case, you don’t need to pass any arguments via *--task-args/--task-args-file*, but as soon as you start this task, Rally will automatically unfold the for-loop for you:

.. code-block:: console

    $ rally task start task.yaml
    --------------------------------------------------------------------------------
     Preparing input task
    --------------------------------------------------------------------------------

    Input task is:
    ---

      KeystoneBasic.create_user:

        -
          args: {}
          runner:
            type: "constant"
            times: 10
            concurrency: 2
          sla:
            failure_rate:
              max: 0

        -
          args: {}
          runner:
            type: "constant"
            times: 10
            concurrency: 4
          sla:
            failure_rate:
              max: 0

        -
          args: {}
          runner:
            type: "constant"
            times: 10
            concurrency: 6
          sla:
            failure_rate:
              max: 0

        -
          args: {}
          runner:
            type: "constant"
            times: 10
            concurrency: 8
          sla:
            failure_rate:
              max: 0

        -
          args: {}
          runner:
            type: "constant"
            times: 10
            concurrency: 10
          sla:
            failure_rate:
              max: 0


    --------------------------------------------------------------------------------
     Task  ea7e97e3-dd98-4a81-868a-5bb5b42b8610: started
    --------------------------------------------------------------------------------

    Benchmarking... This can take a while...

As you can see, the Rally task template syntax is a simple but powerful mechanism that not only enables you to write elegant task configurations, but also makes them more readable for other people. When used appropriately, it can really improve the understanding of your benchmarking procedures in Rally when shared with others.
