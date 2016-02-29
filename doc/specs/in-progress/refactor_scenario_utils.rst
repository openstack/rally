..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode


=========================================================
 Refactor scenarios' utils into central os-services tree
=========================================================

It's hard to reuse code from different scenario utils in areas like context.


Problem description
===================

* Code that wraps openstack services from different scenario utils is
  difficult to reuse in context plugins (or, sometimes in different scenarios
  plugins), which causes code duplications.

* Wrappers don't fully integrate with the current structure (example: network
  operations need to alternate between calls to utils and calls to network
  wrappers).

* It is impossible to do versioning of current utils which makes them
  hard to reuse as a base for out of tree plugins.

* Is is not possible to have separated common functionality (e.g. network) and
  specific implementation features (nova network and neutron)


Proposed change
===============

Group all service related utils under a single tree accessible from all areas
of the project.
Also, inheritance structure in scenarios is problematic. This would be a great
opportunity to move to composition.

Alternatives
------------

None comes to mind.

Implementation
==============

Current source tree
-------------------

.. code-block::

  rally/
  |
  +-- plugins/
      +-- openstack/
      |   +-- scenarios/
      |   |   |
      |   |   +-- nova/
      |   |   |   |
      |   |   |   +-- servers.py
      |   |   |   |
      |   |   |   +-- utils.py
      |   |   |
      |   |   +-- ...
      |   +-- wrappers/
      |       |
      |       +-- keystone.py
      |       |
      |       +-- network.py

keystone scenarios use plugins/openstack/scenarios/keystone/utils.py

.. code-block:: python

    @atomic.action_timer("keystone.create_tenant")
    def _tenant_create(self, name_length=10, **kwargs):
        """Creates keystone tenant with random name.

        :param name_length: length of generated (random) part of name
        :param kwargs: Other optional parameters
        :returns: keystone tenant instance
        """
        name = self._generate_random_name(length=name_length)
        return self.admin_clients("keystone").tenants.create(name, **kwargs)

.. code-block:: python

    class KeystoneBasic(kutils.KeystoneScenario):
        """Basic benchmark scenarios for Keystone."""

        @validation.number("name_length", minval=10)
        @validation.required_openstack(admin=True)
        @scenario.configure(context={"admin_cleanup": ["keystone"]})
        def create_tenant(self, name_length=10, **kwargs):
            """Create a keystone tenant with random name.

            :param name_length: length of the random part of tenant name
            :param kwargs: Other optional parameters
            """
            self._tenant_create(name_length=name_length, **kwargs)

while keystone contexts use
plugins/openstack/wrappers/keystone.py

.. code-block:: python

    @six.add_metaclass(abc.ABCMeta)
    class KeystoneWrapper(object):
        def __init__(self, client):
            self.client = client

        def __getattr__(self, attr_name):
            return getattr(self.client, attr_name)

        @abc.abstractmethod
        def create_project(self, project_name, domain_name="Default"):
            """Creates new project/tenant and return project object.

            :param project_name: Name of project to be created.
            :param domain_name: Name or id of domain where to create project,
                                for implementations that don't support
                                domains this
                                argument must be None or 'Default'.
            """

        @abc.abstractmethod
        def delete_project(self, project_id):
            """Deletes project."""


    class KeystoneV2Wrapper(KeystoneWrapper):
        def create_project(self, project_name, domain_name="Default"):
            self._check_domain(domain_name)
            tenant = self.client.tenants.create(project_name)
            return KeystoneV2Wrapper._wrap_v2_tenant(tenant)

        def delete_project(self, project_id):
            self.client.tenants.delete(project_id)

    class KeystoneV3Wrapper(KeystoneWrapper):
        def create_project(self, project_name, domain_name="Default"):
            domain_id = self._get_domain_id(domain_name)
            project = self.client.projects.create(
                name=project_name, domain=domain_id)
            return KeystoneV3Wrapper._wrap_v3_project(project)

        def delete_project(self, project_id):
            self.client.projects.delete(project_id)

Users context:

.. code-block:: python

    @context.configure(name="users", order=100)
    class UserGenerator(UserContextMixin, context.Context):
        """Context class for generating temporary
           users/tenants for benchmarks."""

        def _create_tenants(self):
            cache["client"] = keystone.wrap(clients.keystone())
            tenant = cache["client"].create_project(
                self.PATTERN_TENANT % {"task_id": task_id, "iter": i}, domain)

Suggested change
----------------

.. code-block::

  plugins/
   |
   +-- openstack/
       |
       |
       +-- scenarios/
       |   |
       |   |
       |   +-- neutron/
       |   +-- authenticate/
       |
       +-- services/
           |  # Here we will store base code for openstack services.
           |  # like wait_for, and wait_for_delete
           +-- base.py
           |
           +-- compute/
           |   |
           |   +-- compute.py
           |
           +-- identity/
           |   | # Here is common service when we care to do things
           |   | # and regardless of which API/service is used for
           |   | # that. So we will implement here parts that can be
           |   | # done in both.
           |   +-- identity.py
           |   | # Here is api for working with specific API
           |   | # version/service Like keystone_v2/keystone_v3 or
           |   | # nova_network/neutron. This will be used in
           |   | # main.py for implementation.
           |   +-- kestone_v2.py
           |   |
           |   +-- kestone_v3.py
           |
           +-- network/
           |   | # Here is common service when we care to do things
           |   | # and regardless of which API/service is used for
           |   | # that. So we will implement here parts that can be
           |   | # done in both.
           |   +-- network.py
           |   | # Here is api for working with specific API
           |   | # version/service Like nova_network/neutron.
           |   | # This will be used in main.py for implementation.
           |   +-- nova_network.py
           |   |
           |   +-- neutron.py
           |
           +-- ...


Base class that allow us to use atomic actions in services is inside the
rally/plugins/openstack/services/base.py:


.. code-block:: python

    class Service(object):
        def __init__(self, clients, atomic_inst=None):
            self.clients = clients
            if atomic_inst:
                if not isinstance(atomic_inst, ActionTimerMixin):
                    raise TypeError()

                # NOTE(boris-42): This allows us to use atomic actions
                #                 decorators but they will add values
                #                 to the scenario or context instance
                self._atomic_actions = atomic_inst._atomic_actions
            else:
                # NOTE(boris-42): If one is using this not for scenarios and
                #                 context, Service instance will store atomic
                #                 actions data.
                self._atomic_actions = costilus.OrderedDict()


Implementation of IdentityService in services/identity/identity.py:


.. code-block:: python

    class IdentityService(Service):
        """Contains only common methods for Keystone V2 and V3."""

        def __init__(self, clients, atomic_inst=None, version=None):
            super(self).__init__(clients, atomic_inst=atomic_inst)

            if version:
                if version == "2":
                    self.impl = KeystoneV2Service()
                else:
                    self.impl = KeysotneServiceV3()
            else:
                self.impl = auto_discover_version()

        def project_create(self, name, **kwargs):
            result =  self.impl.project_create(name)
            # handle the difference between implementations
            return magic(result)

        # ...


Inside services/identity/keystone_v2.py:

.. code-block:: python

    class KeystoneV2Service(KeystoneService):

        # NOTE(boris-42): we can use specific atomic action names
        #                 for specific implementation of service
        @atomic.action_timer("keystone_v2.tenant_create")
        def project_create(self, project_name):
            """Implementation."""


Inside services/identity/keystone_v3.py:

.. code-block:: python

    class KeystoneV3Service(KeystoneService):

        @atomic.action_timer("keystone_v3.project_create")
        def project_create(self, project_name):
            """Implementation."""

        def domain_create(self, *args, **kwargs):
            """Specific method for KesytoneV3."""


Both context.keystone and scenario.keystone can use now services/identity.py

usage is the same in context and scenario, so it's enough to show in case
of scenario.

.. code-block:: python

    from rally.plugins.openstack.services.identity import identity
    from rally.plugins.openstack.services.identity import keystone_v3

    class KeystoneBasic(scenario.OpenStackScenario):  # no more utils.py
        """Basic benchmark scenarios for Keystone."""


        @validation.number("name_length", minval=10)
        @validation.required_openstack(admin=True)
        @scenario.configure(context={"admin_cleanup": ["keystone"]})
        def create_tenant(self, name_length=10, **kwargs):
            """Create a keystone tenant with random name.

            :param name_length: length of the random part of tenant name
            :param kwargs: Other optional parameters
            """

            name = self._generate_random_name(length=name_length)
            # NOTE(boris-42): Code above works in keystone V2 and V3
            #                 as well it will add atomic action, and name
            #                 will be "keystone_v3.project_create" or
            #                 "keystone_v2.tenant_create" depending on used
            #                 version
            common.Identity(self.clients, self).create_project(name,
                                                               **kwargs)

            # NOTE(boris-42): If you need specific operation for keystone v3
            keystone_v3.KeystoneV3Service(self.clients, self).domain_create()

            # NOTE(boris-42): One of the nice thing is that we can move
            #                 initialization of services to __init__ method
            #                 of sceanrio.

Assignee(s)
-----------

  - boris-42

Work Items
----------

#. Create a base.Service class
#. Create for each project services
#. Use in all scenarios and context services instead of utils
#. Deprecate utils
#. Remove utils


Dependencies
============

none
