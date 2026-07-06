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

.. _plugins_resource_type_plugin:


Resource type as a plugin
=========================

A scenario takes its inputs as arguments, but some are not usable as written:
a file path must be read into the file's contents, or a human-friendly image
name must be resolved to the concrete image id an API expects. A scenario
*could* do that itself, but it usually should not: the work is often costly,
identical on every iteration, and unrelated to what the scenario measures, so
it does not belong in the timed loop.

Rally handles this with a pluggable **pre-processing** step. Such an input is
called a *resource*, and a **resource type** is the plugin that turns the value
written in the task into the value the scenario's ``run()`` finally receives.
It is a subclass of ``rally.task.types.ResourceType`` whose ``pre_process()``
runs once per workload (not once per iteration) before the scenario starts.
A few built-in examples:

* ``file`` reads a file path and returns the file's *contents*;
* ``file_dict`` reads a list of paths and returns a ``{path: contents}`` map;
* the OpenStack ``glance_image`` finds an image based on name, regex or
  spec dict.

The resource types available in your installation are listed under
`Available resource types`_ below.

Creating a resource type
^^^^^^^^^^^^^^^^^^^^^^^^

Inherit from ``ResourceType``, register it with ``@plugin.configure``, and
implement ``pre_process()`` with the keyword-only signature below (the older
two-argument form is deprecated, see `Legacy resource types (deprecated)`_):

.. code-block:: python

    import os
    import typing as t

    from rally.common.plugin import plugin
    from rally.task import types


    @plugin.configure(name="text_file")
    class TextFile(types.ResourceType):
        """Read a text file and return its contents."""

        def pre_process(
            self,
            *,
            resource_spec: str,
            config: types.ConvertConfig,
            output_type: t.Any,
        ) -> str:
            with open(os.path.expanduser(resource_spec)) as f:
                return f.read()

``pre_process()`` is called once per workload for each bound argument and
receives:

* ``resource_spec`` is the value written for the argument in the task (its
  pre-conversion specification). Its type annotation is the schema the input is
  validated against and documented from, so annotate it with a concrete type
  (a scalar, a ``TypedDict``, a union) or leave it ``Any`` to accept anything;
  wrap it in ``Annotated[T, typeutils.Field(...)]`` (from ``rally.utils``) for
  extra constraints or a description.
* ``config`` is the ``{"type": ...}`` mapping from ``Convert`` /
  ``@types.convert``, typed ``types.ConvertConfig``. To read extra keys (e.g.
  ``Convert("text_file", encoding="latin-1")``), annotate ``config`` with a
  ``ConvertConfig`` subclass that declares them; that narrows the parameter.
* ``output_type`` is a framework-supplied input for the richer resolution
  shown in `Advanced resource types`_; a converter that does not need it just
  accepts and ignores it, as above.

It returns the value ``run()`` receives, ``None`` to leave the argument
untouched, or a :class:`DeferredResource` to finish resolving per iteration.
The running scenario class is available as ``self._scenario_cls`` (e.g. to read
its validators to understand the specifics of the workload).
Resolving a spec is often expensive (an API lookup), so results can be cached
in ``self._cache``, shared across the resource type's arguments in a workload.

Binding an argument to a scenario
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A scenario binds one of its arguments to a resource type by name. The preferred
form is inline in the argument's annotation, which describes the
*post-conversion* value ``run()`` receives:

.. code-block:: python

    import typing as t

    from rally.task import scenario
    from rally.task import types


    @scenario.configure(name="ScenarioPlugin.example")
    class Example(scenario.Scenario):

        def run(
            self,
            content: t.Annotated[str, types.Convert("text_file")],
            image: t.Annotated[str, types.Convert("glance_image")],
        ) -> None:
            ...

The equivalent decorator form is also supported (the inline ``Convert(...)``
annotation wins if an argument is declared both ways):

.. code-block:: python

    @types.convert(content={"type": "text_file"},
                   image={"type": "glance_image"})
    @scenario.configure(name="ScenarioPlugin.example")
    class Example(scenario.Scenario):

        def run(self, content: str, image: str) -> None:
            ...

Because the value written in the task (the pre-conversion specification)
differs from what ``run()`` receives (the resolved resource), such an argument
is validated against the schema derived from the resource type's
``resource_spec`` annotation rather than against the ``run()`` annotation. A
resource type whose ``resource_spec`` is ``Any`` accepts any specification.

Advanced resource types
^^^^^^^^^^^^^^^^^^^^^^^

The framework-supplied inputs let a resource type do more than a fixed
one-to-one transform. It can:

* vary the returned shape (an id or the whole object) by how the scenario
  argument is typed;
* resolve the value **per iteration**, once the iteration's identity (user,
  project, clients) is known, e.g. picking a resource visible to the current
  user.

.. code-block:: python

    import typing as t

    from rally.common.plugin import plugin
    from rally.task import types


    @plugin.configure(name="glance_image")
    class GlanceImage(types.ResourceType):

        def pre_process(
            self,
            *,
            resource_spec: str,
            config: types.ConvertConfig,
            output_type: t.Any,
        ) -> t.Any:
            images = self._list_matching(resource_spec)   # full objects, once
            want_id = output_type in (str, None)          # decide the shape now
            by_project = {
                img["owner"]: (img["id"] if want_id else img)
                for img in images
            }
            return _ByProject(by_project)           # already the right shape

``output_type`` is the base type of the argument's annotation (``str`` for
``image: t.Annotated[str, Convert("glance_image")]``), so the return shape can
follow the declared type. The annotation is static, so that choice is made here
rather than per iteration.

For per-iteration work, return a ``types.DeferredResource``, whose
``resolve(scenario)`` the framework calls once per iteration, after the
scenario instance is built and before ``run()``. It receives the scenario,
whose narrowed context and user-scoped clients are available:

.. code-block:: python

    class _ByProject(types.DeferredResource):

        def __init__(self, by_project):
            self.by_project = by_project

        def resolve(self, scenario):
            return self.by_project[scenario.context["project"]["id"]]

A ``DeferredResource`` must be picklable: it is deep-copied per iteration and
sent to worker processes, so it holds only plain data (ids, pre-fetched
values), never a live client. Do the expensive lookup once when building it and
keep ``resolve`` cheap and side-effect-free, since it runs inside the timed
iteration.

Legacy resource types (deprecated)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Older resource types implement only the two positional parameters::

    def pre_process(self, resource_spec, config):
        ...

Rally detects this form automatically from the ``pre_process`` signature (the
absence of ``output_type``), invokes it only for an argument present in the
task, and logs a deprecation warning. It still works but cannot resolve per
iteration and will be removed; write new resource types with the keyword-only
contract above.

Available resource types
^^^^^^^^^^^^^^^^^^^^^^^^^

.. generate_plugin_reference::
   :base_cls: Resource Type
