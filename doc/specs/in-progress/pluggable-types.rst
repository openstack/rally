..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Make Resource Types Pluggable
=============================

Rally's current type resolution subsystem (``rally.task.types``) isn't
easily pluggable, is tied to OpenStack, and cannot handle resources
that must be resolved by the context of each iteration rather than the
context of the subtask. This spec aims to solve all three problems.

Problem description
===================

The Rally ``types.set()`` decorator is used to convert resource names
or regular expressions to resource objects. For instance, in a task
file a user can specify:

.. code-block:: yaml

    image:
      regex: cirros-.*-uec
    flavor:
      name: m1.tiny

Rally will convert those into the matching image ID and flavor ID. As
it currently exists, this process has several shortcomings and bugs:

* Although it is technically pluggable, the resource type classes do
  not call ``rally.common.plugin.configure`` and the code is not
  patterned as a plugin, with code in ``rally.plugins``. Technically,
  a user could implement a subclass of
  ``rally.task.types.ResourceType`` in a plugin and use it, but this
  is not obvious from the code or documentation, and it would not be
  registered as a plugin. Moreover, OpenStack-specific resources are
  in the ``rally.task.types`` module instead of the OpenStack plugin.
* It is tied to OpenStack. ``rally.task.types.preprocess()`` loads an
  OpenStack Clients object and passes it to the resource type objects.
* In some cases, resources must be loaded by the client context
  created for each iteration, not by the admin context. For instance,
  when Glance images are created by the ``images`` context they are
  created as private images in each tenant; trying to load the image
  with the admin context fails. We need to be able to support this use
  case, without taking on a significant or universal performance
  penalty.

Proposed change
===============

This change is very involved and is broken into a number of distinct
sections.

Create ``types.convert()``
--------------------------

First, we will add a new function, ``types.convert()``, to replace
``types.set()``. ``types.convert()`` will accept arguments differently
than ``types.set()``. For instance, this:

.. code-block:: python

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)

...will change to:

.. code-block:: python

    @types.convert(image={"type": "glance_image"},
                   flavor={"type": "nova_flavor"})

This has a number of advantages:

* Resource type classes can be named or removed, or the interface
  changed, without breaking the public API.
* Users will not have to import types in the code. Currently this is
  only a single module, but this spec proposes to change that.
* Plugins are loaded automatically, rather than users having to import
  them explicitly.
* We can use the existing plugin deprecation mechanisms.
* By passing a dict to ``types.convert()`` instead of a class, we
  could in theory pass arguments to the types. Nothing in this spec
  requires that functionality, but it is provided for the future.
* ``set`` is a reserved keyword, so by renaming the function we
  eliminate a bit of code that is in violation of the OpenStack Style
  Guidelines.

Convert ``ResourceType`` to plugin
----------------------------------

Next, the code will be rearranged to make it obviously pluggable,
and a ``types.configure()`` call will be added to register the
``ResourceType`` subclasses as plugins. OpenStack resources will be
moved into the OpenStack plugin space, and documentation will be added
to make it clear that ``ResourceType`` can be subclassed by other
plugins. The old resource type classes will be left in place, but
deprecated. ``types.set()`` will also be deprecated at this point.

Switch scenarios to ``types.convert()`` and new type plugins
------------------------------------------------------------

After resource type plugins are created, all existing scenarios will
be changed over to ``types.convert()``. This will allow us to make the
changes below that affect the type conversion API without having to
make further changes to the scenarios.

Change type preprocessing signature
-----------------------------------

The arguments with which each preprocessor is called will be
changed. Instead of:

.. code-block:: python

    def transform(cls, clients, resource_config):

...it will be:

.. code-block:: python

    def preprocess(self, resource_config, context=None, clients=None):

Within the types subsystem proper, only ``context`` will be passed;
``clients`` will remain for compatibility with the validation
subsystem, which does not have a context object yet, and remains tied
to OpenStack.

If ``clients`` is not passed to ``transform()``, the responsibility
for creating OpenStack clients (or doing anything else with the
subtask context) will lie with the ``ResourceType`` subclass
itself. This entails a small performance penalty, but it's necessary
to divorce the types subsystem from OpenStack. If ``clients`` is
passed, then a deprecation warning will be logged. When the validation
subsystem is made independent from OpenStack, the ``clients`` keyword
argument should be removed.

This also makes it so that ``ResourceType.transform()`` is no longer a
class method, which will allow the resource classes to retain
persistent information about a single decorated scenario
function. ``transform`` will also be renamed to ``preprocess``, which
will be more consistent with ``rally.task.types.preprocess`` and will
make it easier to add a second resource type resolution hook,
described below.

Add ``ResourceType.map_for_scenario()``
---------------------------------------

A new hook will be added to the runners. In addition to
``ResourceType.preprocess()``, which is run after contexts but before
the scenarios start, ``ResourceType.map_for_scenario(self,
scenario_context, resource_config)`` will run before each iteration of the
scenario. Together with the change to make ``types.set()`` accept
objects instead of classes, this will solve the issue of resources
that must be resolved per-iteration.

For instance, to resolve images, ``ImageResourceType.preprocess()``
would resolve images for each set of credentials created for the
subtask, as well as for the admin credentials, and cache them;
``ImageResourceType.map_for_scenario()`` would be passed the mapped
scenario context and the resource configuration, and would choose the
correct image ID to pass to the scenario. Note that image listing and
resolution is not done by ``map_for_scenario()``; we should strive to
keep the performance profile of ``map_for_scenario()`` as small as
possible.

In order to simplify the type resolution workflow, only
``map_for_scenario()`` will be able to rewrite arguments, but the
default implementation in ``rally.task.types.ResourceType`` will
rewrite it with the value cached in ``preprocess()``. For instance:

.. code-block:: python

    class ResourceType(plugin.Plugin):

        @abc.abstractmethod
        def preprocess(self, context, resource_config):
            pass

        @abc.abstractmethod
        def map_for_scenario(self, scenario_context, resource_config):
            pass


    class FlavorResourceType(ResourceType):
        def preprocess(self, resource_config, context=None, clients=None):
            self._flavor_id = resource_config.get("id")
            if not self._flavor_id:
                novaclient = clients.nova()
                self._flavor_id = _id_from_name(
                    resource_config=resource_config,
                    resources=novaclient.flavors.list(),
                    typename="flavor")

        def map_for_scenario(self, scenario_context, resource_config):
            return self._flavor_id


    class ImageResourceType(ResourceType):
        def preprocess(self, resource_config, context=None, clients=None):
            self._image_id = resource_config.get("id")
            if not self._image_id:
                self._images = {}
                all_images = clients.glance().images.list()
                for image in all_images:
                    self._images.setdefault(image["owner"], []).append(image)

        def map_for_scenario(self, scenario_context, resource_config):
            if self._image_id:
                return self._image_id
            else:
                return _id_from_name(
                    resource_config=resource_config,
                    resources=self._images[scenario_context["user"]],
                    typename="image")

This demonstrates two different workflows.

Flavors, which exist globally for all users and tenants, can be easily
resolved once, at preprocessing time, and ``map_for_scenario()`` needs
only to substitute the single, canonical flavor ID on each
iteration. This does lead to some redundancy -- flavor arguments will
be rewritten on each iteration, for instance -- but as it's only a
matter of changing a few values in the argument dict, the performance
penalty will be minimal.

Images are more complicated, because images can exist on a per-user
basis, and remain invisible to other users. In order to properly
resolve image IDs, we must first find all images in ``preprocess()``,
and then select the correct image for each iteration (and for the user
that maps to each iteration) in ``map_for_scenario()``.

Remove deprecated code
----------------------

Finally, in some future release we will remove the old, deprecated
resource type classes and ``types.set()``.

Alternatives
------------

Type resolution could be done in a single step (as opposed to the two
step ``preprocess()``/``map_for_scenario()``) if we passed the results in
the context object instead of rewriting scenario arguments. This is
less straightforward, though; the scenario author would then need to
know where to look in the context to find the resource object, even
though for any given iteration there is exactly one resource object
that is appropriate.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  stpierre aka Chris St. Pierre

Work Items
----------

* Create ``types.convert()``.
* Rearrange the code into plugins and add plugin
  documentation. Deprecate ``types.set()`` and the old resource type
  classes.
* Convert existing scenarios to use ``types.convert()``.
* Convert ``ResourceType.transform()`` to
  ``ResourceType.preprocess()`` and create a new abstract intermediate
  subclass, ``OpenStackResourceType``, to which to offload OpenStack
  client creation.
* Add the ``ResourceType.map_for_scenario()`` hook.
* Rewrite any resource types that need to take advantage of the new
  ``map_for_scenario()`` hook. This will likely be limited to
  ``ImageResourceType``  and ``EC2ImageResourceType``. If there are
  obvious patterns that can be abstracted out, then add a new abstract
  intermediate subclass.
* In the indeterminate future, remove the deprecated resource type
  classes and ``types.set()``.

Dependencies
============

None.
