..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _plugins_platform_plugin:


Platform as a plugin
====================

A platform plugin teaches Rally about one kind of target. It knows how to
read a piece of the :ref:`environment spec <env-spec>`, how to check that the
target is alive, and how to clean up after a task.

Rally itself ships no platform plugins. Every platform comes from a plugin
package, like ``existing@openstack`` from ``rally-openstack``.

Creation
^^^^^^^^

Inherit from ``rally.env.platform.Platform`` and register the class with
``@platform.configure()``. It takes two names:

* ``name`` is the name of the plugin
* ``platform`` is the thing the plugin talks to

Together they make the full name that goes into the spec, in the form
``name@platform``. The example below is used as ``existing@myservice``.

Put the schema of your part of the spec into ``CONFIG_SCHEMA``. Rally
validates the spec against it before it creates anything.

.. code-block:: python

    import requests

    from rally.env import platform


    @platform.configure(name="existing", platform="myservice")
    class ExistingMyService(platform.Platform):
        """Describes an already deployed MyService instance."""

        CONFIG_SCHEMA = {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "token": {"type": "string"}
            },
            "required": ["url"],
            "additionalProperties": False
        }

        def create(self):
            # nothing to deploy, the service is already there
            return self.spec, {}

        def destroy(self):
            # and nothing to tear down
            pass

        def check_health(self):
            try:
                resp = requests.get("%s/healthz" % self.spec["url"])
            except Exception as e:
                return {"available": False, "message": str(e)}
            if resp.status_code != 200:
                return {
                    "available": False,
                    "message": "MyService answered with %s" % resp.status_code
                }
            return {"available": True}

        def info(self):
            resp = requests.get("%s/version" % self.spec["url"])
            return {"info": {"version": resp.json()["version"]}}

The spec of the plugin is available as ``self.spec``.

An environment with this plugin looks like this:

.. code-block:: json

    {
        "existing@myservice": {
            "url": "http://example.net:8080"
        }
    }

The API
^^^^^^^

.. autoclass:: rally.env.platform.Platform
   :members: create, destroy, cleanup, check_health, info,
             _get_validation_context, create_spec_from_sys_environ, update
   :member-order: bysource

If :meth:`check_health`, :meth:`info`, :meth:`cleanup` or
:meth:`create_spec_from_sys_environ` raises or returns something that does
not match the described format, Rally reports that the plugin is broken. It
does not crash the whole run.

Usage
^^^^^

Once the package with your plugin is installed, the platform can be used in a
spec right away:

.. code-block:: console

   $ rally env create --name=my-service --spec myservice.json
   $ rally env check
   $ rally env info

See :ref:`env-component` for the rest of the environment workflow.
