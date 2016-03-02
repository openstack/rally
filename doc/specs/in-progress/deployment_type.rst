..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Rally Deployment Unification
============================

Make Rally be able to examine any software through the API,
unbound it from OpenStack.


Problem description
===================

Rally is able to examine only system that use Keystone as a authentication
services, which limits sphere where Rally is suitable.

At the moment to run Rally Task or Rally Verify you must specify OpenStack
deployment which contains credentials of it. These credentials are used in
Rally Task & Verify for different setups and validations.

Rally is not able to store more than one credential for one deployment, so
it is impossible to support multi-scenario runs related to different systems.


Proposed change
===============

* Modify 'Deployment' database model to be able to store credentials
  of many different systems, adding type of system.

Now we have model Deployment with admin and users columns,
which are credentials for Keystone (tight coupled with OpenStack).

There is next model now:

.. code-block:: python

    class Deployment(BASE, RallyBase):
        ...
        admin = sa.Column(types.PickleType, nullable=True)
        users = sa.Column(types.PickleType, default=[], nullable=False)
        ...

and values of columns in DB something like that:

``admin = {admin_creds} or None``

``users = [{user_creds1}, {user_creds2}, ...] or []``

We need to decouple deployment from OpenStack and
make credentials more flexible, we describe it in one column named
``credentials``, where we can store special structure containing credentials
for many different systems, including type of credentials for each.

.. code-block:: python

    class Deployment(BASE, RallyBase):
        ...
        credentials = sa.Column(types.PickleType, default=[], nullable=False)
        ...

So, for current OpenStack credentials we will have next data
in credentials column in DB after migration:

.. code-block:: python

    credentials = [
        [
            "openstack",
            {admin: {admin_creds} or None,
             users: [{user_creds1}, {user_creds2}, ...] or []}
        ],
    ]

and for multi-credentials deployment:

.. code-block:: python

    credentials = [
        [
            "openstack",
            {admin: {admin_creds} or None,
             users: [{user_creds1}, {user_creds2}, ...] or []}
        ],
        [
            "zabbix",
            {"url": "example.com", "login": "admin", "password": "admin"}
        ]
    ]

Future summarized schema in DB:
``credentials = [[<type>, <Credentials>], ... ]``

To implement this point we need to write db migration, tests for it
and write adapters for credentials get/create/update methods,
mostly for support backward compatibility in ``rally.api`` module methods.

* Get rid of ``rally.common.objects.credential.Credential`` class
  and fix it usages mostly in ``rally.osclients`` if needed.

Refactor all usages of passing ``rally.common.objects.credential.Credential``
to ``rally.osclients.OSClient``, make possible to take dict as credentials
for ``rally.osclients.OSClient`` class, initialise
``rally.plugins.openstack.credentials.OpenStackCredentials`` class
in ``OSClient`` ``__init__`` method.

Base class for credentials will be inherited from plugins.Plugin
and must implement validation method,
it will be placed in ``rally.plugins.common.credentials``:

.. code-block:: python

    @six.add_metaclass(abc.ABCMeta)
    @plugin.configure(name="base_credentials", schema="{...}")
    class Credentials(plugin.Plugin):
        def __init__(self, credentials):
            self.validate(credentials)
            super(Credentials, self).__setattr__("credentials", credentials)

        def __getattr__(self, item):
            if item in self.__dict__:
                return self.__dict__[item]
            return self.credentials[item]

        def __setattr__(self, key, value):
            self.credentials[key] = value

        def to_dict(self):
            return self.credentials.copy()

        def validate(self, obj):
            jsonschema.validate(obj, self._meta_get("schema"))

and we need to add child for openstack credentials,
it will be placed in ``rally.plugins.openstack.credentials``:

.. code-block:: python

    openstack_credentials_schema = {
        "type": "object",

        "properties": {
            "auth_url": {"type": "string"},
            "username": {"type": "string"},
            "password": {"type": "string"},
        },
        "required": ["auth_url", "username", "password"]
    }

    @plugin.configure(name="openstack_credentials",
                      schema=openstack_credentials_schema)
    class OpenStackCredentials(Credentials):
        pass

Replace usage of ``rally.common.objects.credential.Credential`` to
``rally.plugins.openstack.credentials.OpenStackCredentials``
in ``rally.osclients``

* Update cli to show deployment type in output of 'rally deployment list'.

Make possible to show deployments list in case of multi-scenario as:

.. code-block:: shell

    > rally deployment list # (in case of many deployments)

    uuid   | name   | created_at | type      | credential
    -------+--------+------------+-----------+---------------------------------
    <uuid> | <name> | 21-02-2016 | openstack | {"admin": {...}, "users": [...]}
                                 | zabbix    | {"login": "login", "psw": "..."}


Alternatives
------------

None


Implementation
==============



Assignee(s)
-----------

Primary assignee:
  rpromyshlennikov aka Rodion Promyshlennikov (rpromyshlennikov@mirantis.com)


Work Items
----------

- Change Deployment db model class
- Write migrations
- Make adapters for credentials get/create/update methods for temporary
  support changed data format
- Remove all usages of passing ``rally.common.objects.credential.Credential``
  to ``rally.osclients.OSClient``
- Create new plugin based class for credentials
- Write subclass of rally.plugins.common.credentials.Credential
  for OpenStack credentials with proper validation of them
- Migrate to new credentials class
- Remove ``rally.common.objects.credential.Credential`` class
- Improve CLI-client to make possible show multi-credentials deployments.
- Feature refactoring: remove adapters after
  "Multi Scenario support" implementation.

Dependencies
============

None
