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

.. _plugins_context_plugin:


Context as a plugin
===================

So what are contexts doing? These plugins will be executed before
scenario iteration starts. For example, a context plugin could create
resources (e.g., download 10 images) that will be used by the
scenarios. All created objects must be put into the *self.context*
dict, through which they will be available in the scenarios. Let's
create a simple context plugin that adds a flavor to the environment
before the benchmark task starts and deletes it after it finishes.

Creation
^^^^^^^^

Inherit a class for your plugin from the base *Context* class. Then,
implement the Context API: the *setup()* method that creates a flavor and the
*cleanup()* method that deletes it.

.. code-block:: python

    from rally.task import context
    from rally.common import logging
    from rally import consts
    from rally import osclients

    LOG = logging.getLogger(__name__)


    @context.configure(name="create_flavor", order=1000)
    class CreateFlavorContext(context.Context):
        """This sample creates a flavor with specified options before task starts
        and deletes it after task completion.

        To create your own context plugin, inherit it from
        rally.task.context.Context
        """

        CONFIG_SCHEMA = {
            "type": "object",
            "$schema": consts.JSON_SCHEMA,
            "additionalProperties": False,
            "properties": {
                "flavor_name": {
                    "type": "string",
                },
                "ram": {
                    "type": "integer",
                    "minimum": 1
                },
                "vcpus": {
                    "type": "integer",
                    "minimum": 1
                },
                "disk": {
                    "type": "integer",
                    "minimum": 1
                }
            }
        }

        def setup(self):
            """This method is called before the task starts."""
            try:
                # use rally.osclients to get necessary client instance
                nova = osclients.Clients(self.context["admin"]["credential"]).nova()
                # and than do what you need with this client
                self.context["flavor"] = nova.flavors.create(
                    # context settings are stored in self.config
                    name=self.config.get("flavor_name", "rally_test_flavor"),
                    ram=self.config.get("ram", 1),
                    vcpus=self.config.get("vcpus", 1),
                    disk=self.config.get("disk", 1)).to_dict()
                LOG.debug("Flavor with id '%s'" % self.context["flavor"]["id"])
            except Exception as e:
                msg = "Can't create flavor: %s" % e.message
                if logging.is_debug():
                    LOG.exception(msg)
                else:
                    LOG.warning(msg)

        def cleanup(self):
            """This method is called after the task finishes."""
            try:
                nova = osclients.Clients(self.context["admin"]["credential"]).nova()
                nova.flavors.delete(self.context["flavor"]["id"])
                LOG.debug("Flavor '%s' deleted" % self.context["flavor"]["id"])
            except Exception as e:
                msg = "Can't delete flavor: %s" % e.message
                if logging.is_debug():
                    LOG.exception(msg)
                else:
                    LOG.warning(msg)


Usage
^^^^^

You can refer to your plugin context in the benchmark task configuration
files in the same way as any other contexts:

.. code-block:: json

    {
        "Dummy.dummy": [
            {
                "args": {
                    "sleep": 0.01
                },
                "runner": {
                    "type": "constant",
                    "times": 5,
                    "concurrency": 1
                },
                "context": {
                    "users": {
                        "tenants": 1,
                        "users_per_tenant": 1
                    },
                     "create_flavor": {
                        "ram": 1024
                    }
                }
            }
        ]
    }
