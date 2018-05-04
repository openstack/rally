=============
Rally v0.12.0
=============

+------------------+-----------------------+
| Release date     |     **05/08/2018**    |
+------------------+-----------------------+

.. warning:: It is friendly reminder about the future of in-tree OpenStack
    plugins. All further development is done in
    `a separate project <https://github.com/openstack/rally-openstack>`_.
    In-tree plugins are deprecated and will be removed in next major release!

* Improve performance of *rally task import* command.

* Port internals of Verification component to support pip 10

* Extend plugins interface to provide config options to load.
  An example of *setup.cfg*/*setup.py*:

  .. code-block::

    [entry_points]
    rally_plugins =
        path = rally_openstack
        options = rally_openstack.cfg.opts:list_opts

  Method *list_opts* in the above example, returns a dict where key is a
  category name, value is a list of options.

* Rework *ResourceType* plugin type. Previously, it was hard-coded for
  OpenStack resources only (initialization of OpenStack clients).

  An old interface looked like:

  .. code-block:: python

      from rally.common.plugin import plugin
      from rally.task import type

      @plugin.configure(name="glance")
      class GlanceResource(type.ResourceType):
          @classmethod
          def transform(cls, clients, resource_config):
              """Transform the resource config to id.

              :param clients: Initialized OpenStack clients
              :param resource_config: a dict with resource description
                  taken from workload
              """
              pass

  The new one:

  .. code-block:: python

      from rally.common.plugin import plugin
      from rally.task import type

      @plugin.configure(name="glance")
      class GlanceResource(type.ResourceType):
          def __init__(self, context, cache=None):
              """init method

              :param context: A context object as like other plugins accept.
              :param cache: A global cache which can be used for listing
                  the similar resources.
              """
              super(GlanceResource, self).__init__(context, cache)
              # NOTE #1: the next code is copy-pasted from
              #    *rally_openstack.types.OpenStackResourceType* class and
              #    there is no need to copy it to plugins itself, just inherit
              #    from the right parent.
              # NOTE #2: the following code is equal to what we have in
              #    an old ResourceType implementation. Property *self._clients*
              #    is what was transmitted to transform method as *clients*
              #    argument
              self._clients = None
              if self._context.get("admin"):
                  self._clients = osclients.Clients(
                      self._context["admin"]["credential"])
              elif self._context.get("users"):
                  self._clients = osclients.Clients(
                      self._context["users"][0]["credential"])

          def pre_process(self, resource_spec, config):
              """Pre process the resource config to id.

              :param resource_spec: a dict with resource description
                  taken from workload
              :param config: A resource specification from scenario
                  plugin. Usually it contains only *type* of resource.
              """
              #
              pass

Fixed bugs
~~~~~~~~~~

* Fix deprecated *--tasks* argument of *rally task report*.
  Use *--uuid* instead.

* Fix printing warning of an old deprecated deployment configuration format.

Thanks
~~~~~~

 2 Everybody!
