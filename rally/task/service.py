#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import functools
import inspect

import six

from rally.common.plugin import discover
from rally.common.plugin import meta
from rally import exceptions
from rally.task import atomic


def service(service_name, service_type, version, client_name=None):
    """Mark class as an implementation of partial service APIs.

    :param service_name: name of the service (e.g. Nova)
    :type service_name: str
    :param service_type: type of the service (e.g. Compute)
    :type service_type: str
    :param version: version of service (e.g. 2.1)
    :type version: str
    :param client_name: name of client for service. If None, service_name will
        be used instead.
    :type client_name: str
    """
    def wrapper(cls):
        cls._meta_init()
        cls._meta_set("name", service_name.lower())
        cls._meta_set("type", service_type.lower())
        cls._meta_set("version", str(version))
        cls._meta_set("client_name", client_name or service_name)
        return cls
    return wrapper


def compat_layer(original_impl):
    """Set class which should be unified to common interface

    :param original_impl: implementation of specific service API
    :type original_impl: cls
    """
    def wrapper(cls):
        cls._meta_init()
        cls._meta_set("impl", original_impl)
        return cls
    return wrapper


def should_be_overridden(func):
    """Mark method which should be overridden by subclasses."""
    func.require_impl = True
    return func


def method_wrapper(func):
    """Wraps service's methods with some magic

    1) Each service method should not be called with positional arguments,
       since it can lead mistakes in wrong order while writing version
       compatible code. We had such situation in KeystoneWrapper
       (see https://review.openstack.org/#/c/309470/ ):

       .. code-block:: python

           class IdentityService(Service):
               def add_role(self, role_id, user_id, project_id):
                   self._impl(role_id, user_id, project_id)

           class KeystoneServiceV2(Service):
               def add_role(self, user_id, role_id, project_id):
                   pass

           class KeystoneServiceV3(Service):
               def add_role(self, role_id, user_id, project_id):
                   pass

       Explanation of example: The signature of add_role method is
       different in KeystoneServiceV2 and KeystoneServiceV3. Since
       IdentityService uses positional arguments to make call to
       self._impl.add_role, we have swapped values of role_id and user_id in
       case of KeystoneServiceV2.

       Original code and idea are taken from `positional` library.

    2) We do not need keep atomics for some actions, for example for inner
       actions (until we start to support them). Previously, we used
       "atomic_action" argument with `if atomic_action` checks inside each
       method. To reduce number of similar if blocks, let's write them in one
       place, make the code cleaner and support such feature for all service
       methods.
    """

    @functools.wraps(func)
    def wrapper(instance, *args, **kwargs):
        args_len = len(args)

        if args_len > 1:
            message = ("%(name)s takes at most 1 positional argument "
                       "(%(given)d given)" % {"name": func.__name__,
                                              "given": args_len})

            raise TypeError(message)

        return func(instance, *args, **kwargs)

    return wrapper


class ServiceMeta(type):
    """Alternative implementation of abstract classes for Services.

    Common class of specific Service should not be hardcoded for any version of
    API. We expect that all public methods of specific common class are
    overridden in all versioned implementation.
    """
    def __new__(mcs, name, parents, dct):
        for field in dct:
            if not field.startswith("_") and callable(dct[field]):
                dct[field] = method_wrapper(dct[field])
        return super(ServiceMeta, mcs).__new__(mcs, name, parents, dct)

    def __init__(cls, name, bases, namespaces):
        super(ServiceMeta, cls).__init__(name, bases, namespaces)
        bases = [c for c in cls.__bases__ if type(c) == ServiceMeta]
        if not bases:
            # nothing to check
            return

        # obtain all properties of cls, since namespace doesn't include
        # properties of parents
        not_implemented_apis = set()
        for name, obj in inspect.getmembers(cls):
            if (getattr(obj, "require_impl", False) and
                    # name in namespace means that object was introduced in cls
                    name not in namespaces):
                # it is not overridden...
                not_implemented_apis.add(name)

        if not_implemented_apis:
            raise exceptions.RallyException(
                "%s has wrong implementation. Implementation of specific "
                "version of API should override all required methods of "
                "base service class. Missed method(s): %s." %
                (cls.__name__, ", ".join(not_implemented_apis)))


@six.add_metaclass(ServiceMeta)
class Service(meta.MetaMixin):
    """Base help class for Cloud Services(for example OpenStack services).

    A simple example of implementation:

    .. code-block::

        # Implementation of Keystone V2 service
        @service("keystone", service_type="identity", version="2")
        class KeystoneV2Service(Service):

            @atomic.action_timer("keystone_v2.create_tenant")
            def create_tenant(self, tenant_name):
                return self.client.tenants.create(project_name)

        # Implementation of Keystone V3 service
        @service("keystone", service_type="identity", version="3")
        class KeystoneV3Service(Service):

            @atomic.action_timer("keystone_v3.create_project")
            def create_project(self, project_name):
                return self.client.project.create(project_name)

    """

    def __init__(self, clients, name_generator=None, atomic_inst=None):
        """Initialize service class

        :param clients: instance of rally.plugins.openstack.osclients.Clients
        :param name_generator: a method for generating random names. Usually
            it is generate_random_name method of RandomNameGeneratorMixin
            instance.
        :param atomic_inst: an object to store atomic actions. Usually, it is
            `_atomic_actions` property of ActionTimerMixin instance
        """
        self._clients = clients
        self._name_generator = name_generator

        if atomic_inst is None:
            self._atomic_actions = atomic.ActionTimerMixin().atomic_actions()
        else:
            self._atomic_actions = atomic_inst

        self.version = None
        if self._meta_is_inited(raise_exc=False):
            self.version = self._meta_get("version")

    def generate_random_name(self):
        if not self._name_generator:
            raise exceptions.RallyException(
                "You cannot use `generate_random_name` method, until you "
                "initialize class with `name_generator` argument.")
        return self._name_generator()


class UnifiedService(Service):
    """Base help class for unified layer for Cloud Services

    A simple example of Identity service implementation:

    .. code-block::

        import collections


        Project = collections.namedtuple("Project", ["id", "name"])


        # Unified entry-point for Identity OpenStack service
        class Identity(UnifiedService):

            # this method is equal in UnifiedKeystoneV2 and UnifiedKeystoneV3.
            # Since there is no other implementation except Keystone, there
            # are no needs to copy-paste it.
            @classmethod
            def _is_applicable(cls, clients):
                cloud_version = clients.keystone().version.split(".")[0][1:]
            return cloud_version == impl._meta_get("version")

            def create_project(self, project_name, domain_name="Default"):
                return self._impl.create_project(project_name,
                                                 domain_name=domain_name)


        # Class which unifies raw keystone v2 data to common form
        @compat_layer(KeystoneV2Service)
        class UnifiedKeystoneV2(Identity):
            def create_project(self, project_name, domain_name="Default"):
                if domain_name.lower() != "default":
                    raise NotImplementedError(
                        "Domain functionality not implemented in Keystone v2")
                tenant = self._impl.create_tenant(project_name)
                return Project(id=tenant.id, name=tenant.name)

        # Class which unifies raw keystone v3 data to common form
        @compat_layer(KeystoneV3Service)
        class UnifiedKeystoneV3(Identity):
            def create_project(self, project_name, domain_name="Default"):
                project = self._impl.create_project(project_name,
                                                    domain_name=domain_name)
                return Project(id=project.id, name=project.name)
    """

    def __init__(self, clients, name_generator=None, atomic_inst=None):
        """Initialize service class

        :param clients: instance of rally.plugins.openstack.osclients.Clients
        :param name_generator: a method for generating random names. Usually
            it is generate_random_name method of RandomNameGeneratorMixin
            instance.
        :param atomic_inst: an object to store atomic actions. Usually, it is
            `_atomic_actions` property of ActionTimerMixin instance
        """
        super(UnifiedService, self).__init__(clients, name_generator,
                                             atomic_inst)

        if self._meta_is_inited(raise_exc=False):
            # it is an instance of compatibility layer for specific Service
            impl_cls = self._meta_get("impl")
            self._impl = impl_cls(self._clients, self._name_generator,
                                  self._atomic_actions)
            self.version = impl_cls._meta_get("version")
        else:
            # it is a base class of service
            impl_cls, _all_impls = self.discover_impl()
            if not impl_cls:
                raise exceptions.RallyException(
                    "There is no proper implementation for %s."
                    % self.__class__.__name__)
            self._impl = impl_cls(self._clients, self._name_generator,
                                  self._atomic_actions)
            self.version = self._impl.version

    def discover_impl(self):
        """Discover implementation for service

        One Service can have different implementations(not only in terms of
        versioning, for example Network service of OpenStack has Nova-network
        and Neutron implementation. they are quite different). Each of such
        implementations can support several versions. This method is designed
        to choose the proper helper class based on available services in the
        cloud and based on expected version.

        Returns a tuple with implementation class as first element, a set of
            all implementations as a second element
        """

        # find all classes with unified implementation
        impls = {cls: cls._meta_get("impl")
                 for cls in discover.itersubclasses(self.__class__)
                 if (cls._meta_is_inited(raise_exc=False) and
                     cls._meta_get("impl"))}

        service_names = {o._meta_get("name") for o in impls.values()}

        enabled_services = None
        # let's make additional calls to cloud only when we need to make a
        # decision based on available services
        if len(service_names) > 1:
            enabled_services = list(self._clients.services().values())

        for cls, impl in impls.items():
            if (enabled_services is not None and
                    impl._meta_get("name") not in enabled_services):
                continue
            if cls.is_applicable(self._clients):
                return cls, impls

        return None, impls

    @classmethod
    def is_applicable(cls, clients):
        """Check that implementation can be used in cloud."""

        if cls._meta_is_inited(raise_exc=False):
            impl = cls._meta_get("impl", cls)
            client = getattr(clients, impl._meta_get("client_name"))
            return client.choose_version() == impl._meta_get("version")
        return False


class _Resource(object):

    __slots__ = []
    _id_property = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, item, default=None):
        return getattr(self, item, default)

    def __repr__(self):
        return "<%s id=%s>" % (self.__class__.__name__,
                               getattr(self, self._id_property, "n/a"))

    def __eq__(self, other):
        self_id = getattr(self, self._id_property)
        return (isinstance(other, self.__class__) and
                self_id == getattr(other, self._id_property))

    def _as_dict(self):
        return dict((k, self[k]) for k in self.__slots__)


def make_resource_cls(name, properties, id_property="id"):
    """Construct a resource class with limited number of properties.

    Unlike collections.namedtuple, a created class has user-friendly getitem
    method for obtaining properties.

    :param name: The name of resource (i.e image, container..)
    :param properties: The list of allowed properties
    :param id_property: The name of property which should be used as id of
        resource. By defaults, it is "id" field if such property presents in
        "properties" or first element of "properties" in other cases.
    """

    id_property = id_property if id_property in properties else properties[0]

    # NOTE(andreykurilin): call a `type` method instead of returning just raw
    #   class (create Resource class inside the method make_resource_cls and
    #   return it) allows to setup a custom name of a new class, which will be
    #   used in case of errors and etc
    return type(name.title(), (_Resource,), {"__slots__": properties,
                                             "_id_property": id_property})
