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

Inherit a class for your plugin from the base *OpenStackScenario* class and
implement a scenario method inside it. In our scenario, we'll first
list flavors as an ordinary user, and then repeat the same using admin
clients:

.. code-block:: python

    from rally import consts
    from rally.plugins.openstack import scenario
    from rally.task import atomic
    from rally.task import validation


    @validation.add("required_services", services=[consts.Service.NOVA])
    @validation.add("required_platform", platform="openstack", users=True)
    @scenario.configure(name="ScenarioPlugin.list_flavors_useless")
    class ListFlavors(scenario.OpenStackScenario):
        """Sample plugin which lists flavors."""

        @atomic.action_timer("list_flavors")
        def _list_flavors(self):
            """Sample of usage clients - list flavors

            You can use self.context, self.admin_clients and self.clients
            which are initialized on scenario instance creation"""
            self.clients("nova").flavors.list()

        @atomic.action_timer("list_flavors_as_admin")
        def _list_flavors_as_admin(self):
            """The same with admin clients"""
            self.admin_clients("nova").flavors.list()

        def run(self):
            """List flavors."""
            self._list_flavors()
            self._list_flavors_as_admin()


Validating and documenting arguments with type annotations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``run()`` method's parameters can be annotated with regular Python type
hints. Rally derives a JSON Schema from these annotations and uses it to:

* validate the input ``args`` provided in a task (before the task starts)
* display each parameter's type in ``rally plugin show`` and the
  :ref:`plugin-reference`.

Annotating arguments is the recommended way to declare their types and
constraints. Un-annotated scenarios keep working unchanged.

Rally understands the plain types (``int``, ``float``, ``str``, ``bool``,
``list``, ``dict``), ``typing.Optional`` / ``| None``, ``enum.Enum`` and
``typing.Literal`` for a fixed set of values, parameterized containers such as
``list[str]`` or ``dict[str, int]`` (whose element and value types are also
checked), and multi-type unions like ``int | dict[str, int]`` or
``bool | str | None``.

To constrain the value itself, annotate it with ``scenario.Field``:

.. code-block:: python

    import typing as t

    from rally.task import scenario


    @scenario.configure(name="ScenarioPlugin.boot_servers")
    class BootServers(scenario.Scenario):

        def run(
            self,
            count: t.Annotated[int, scenario.Field(ge=1, le=100)] = 1,
            flavor: str = "m1.small",
            network: t.Literal["public", "private"] = "private",
            description: t.Optional[str] = None,
        ) -> None:
            """Boot a number of servers.

            :param count: how many servers to boot
            :param flavor: flavor name to boot from
            :param network: which network to attach
            :param description: optional free-form description
            """
            ...

An argument that is not annotated, or whose type Rally cannot map, accepts
**any** value and is left unvalidated.

A structured (dict) argument can be described with a ``TypedDict``, whose
fields become individually typed properties:

.. code-block:: python

    import typing_extensions as te


    class BootSpec(te.TypedDict, closed=True):
        name: str                              # required
        count: te.NotRequired[int]             # optional
        admin_pass: te.NotRequired[te.Never]   # forbidden

    def run(self, spec: BootSpec) -> None:
        ...

Two independent axes control the object schema:

* **required keys**: ``total=False`` (or a per-field ``Required`` /
  ``NotRequired``) marks fields optional; the rest are required.
* **extra keys**: extra keys are allowed by default. ``closed=True``
  (:pep:`728`) forbids any key that is not declared, and a field typed
  ``NotRequired[Never]`` forbids that specific key even when the TypedDict is
  open.

.. note::

   mypy 2.x may flag ``closed=`` as an unexpected argument; it works at runtime
   and is honored by Rally. Add ``# type: ignore[call-arg]`` if that check is
   enforced in your project.

Some inputs cannot be used as raw values; they must first be transformed or
discovered (a file path read into its contents, an image name resolved to an
id). Rally does this through a pluggable pre-processing step called a *resource
type*; bind an argument to one inline with ``types.Convert(...)``:

.. code-block:: python

    import typing as t

    from rally.task import types


    def run(
        self,
        image: t.Annotated[str, types.Convert("glance_image")],
    ) -> None:
        ...

The value is then validated against the schema derived from the resource
type's ``resource_spec`` annotation (the schema of the specification), not the
``run()`` annotation. See :ref:`plugins_resource_type_plugin` for how resource
types work, the available types, and the ``@types.convert`` decorator form.

Usage
^^^^^

You can refer to your plugin scenario in the task input files in the same
way as any other scenarios:

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
