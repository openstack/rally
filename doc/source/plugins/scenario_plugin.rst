..
      Copyright 2016 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _plugins_scenario_plugin:


Scenario as a plugin
====================

Let's create a simple scenario plugin that list flavors.

Creation
^^^^^^^^

Inherit a class for your plugin from the base *Scenario* class and
implement a scenario method inside it. In our scenario, we'll first
list flavors as an ordinary user, and then repeat the same using admin
clients:

.. code-block:: python

    from rally.task import atomic
    from rally.task import scenario


    class ScenarioPlugin(scenario.Scenario):
        """Sample plugin which lists flavors."""

        @atomic.action_timer("list_flavors")
        def _list_flavors(self):
            """Sample of usage clients - list flavors

            You can use self.context, self.admin_clients and self.clients which are
            initialized on scenario instance creation"""
            self.clients("nova").flavors.list()

        @atomic.action_timer("list_flavors_as_admin")
        def _list_flavors_as_admin(self):
            """The same with admin clients"""
            self.admin_clients("nova").flavors.list()

        @scenario.configure()
        def list_flavors(self):
            """List flavors."""
            self._list_flavors()
            self._list_flavors_as_admin()


Usage
^^^^^

You can refer to your plugin scenario in the benchmark task
configuration files in the same way as any other scenarios:

.. code-block:: json

    {
        "ScenarioPlugin.list_flavors": [
            {
                "runner": {
                    "type": "serial",
                    "times": 5,
                },
                "context": {
                    "create_flavor": {
                        "ram": 512,
                    }
                }
            }
        ]
    }

This configuration file uses the *"create_flavor"* context which we
created in :ref:`plugins_context_plugin`.
