# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
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

import os

from oslo_config import cfg

from rally.common.i18n import _
from rally.common import log as logging
from rally import consts
from rally import exceptions
from rally import objects


CONF = cfg.CONF

OSCLIENTS_OPTS = [
    cfg.FloatOpt("openstack_client_http_timeout", default=180.0,
                 help="HTTP timeout for any of OpenStack service in seconds"),
    cfg.BoolOpt("https_insecure", default=False,
                help="Use SSL for all OpenStack API interfaces",
                deprecated_for_removal=True),
    cfg.StrOpt("https_cacert", default=None,
               help="Path to CA server cetrificate for SSL",
               deprecated_for_removal=True)
]
CONF.register_opts(OSCLIENTS_OPTS)


def cached(func):
    """Cache client handles."""

    def wrapper(self, *args, **kwargs):
        key = "{0}{1}{2}".format(func.__name__,
                                 str(args) if args else "",
                                 str(kwargs) if kwargs else "")
        if key not in self.cache:
            self.cache[key] = func(self, *args, **kwargs)
        return self.cache[key]

    return wrapper


def create_keystone_client(args):
    from keystoneclient import discover as keystone_discover
    discover = keystone_discover.Discover(**args)
    for version_data in discover.version_data():
        version = version_data["version"]
        if version[0] <= 2:
            from keystoneclient.v2_0 import client as keystone_v2
            return keystone_v2.Client(**args)
        elif version[0] == 3:
            from keystoneclient.v3 import client as keystone_v3
            return keystone_v3.Client(**args)
    raise exceptions.RallyException(
        "Failed to discover keystone version for url %(auth_url)s.", **args)


class Clients(object):
    """This class simplify and unify work with openstack python clients."""

    def __init__(self, endpoint):
        self.endpoint = endpoint
        # NOTE(kun) Apply insecure/cacert settings from rally.conf if those are
        # not set in deployment config. Remove it when invaild.
        if self.endpoint.insecure is None:
            self.endpoint.insecure = CONF.https_insecure
        if self.endpoint.cacert is None:
            self.endpoint.cacert = CONF.https_cacert
        self.cache = {}

    @classmethod
    def create_from_env(cls):
        return cls(
            objects.Endpoint(
                os.environ["OS_AUTH_URL"],
                os.environ["OS_USERNAME"],
                os.environ["OS_PASSWORD"],
                os.environ.get("OS_TENANT_NAME"),
                region_name=os.environ.get("OS_REGION_NAME")
            ))

    def clear(self):
        """Remove all cached client handles."""
        self.cache = {}

    @cached
    def keystone(self):
        """Return keystone client."""
        new_kw = {
            "timeout": CONF.openstack_client_http_timeout,
            "insecure": self.endpoint.insecure, "cacert": self.endpoint.cacert
        }
        kw = self.endpoint.to_dict()
        kw.update(new_kw)
        client = create_keystone_client(kw)
        if client.auth_ref is None:
            client.authenticate()
        return client

    def verified_keystone(self):
        """Ensure keystone endpoints are valid and then authenticate

        :returns: Keystone Client
        """
        from keystoneclient import exceptions as keystone_exceptions
        try:
            # Ensure that user is admin
            client = self.keystone()
            if "admin" not in [role.lower() for role in
                               client.auth_ref.role_names]:
                raise exceptions.InvalidAdminException(
                    username=self.endpoint.username)
        except keystone_exceptions.Unauthorized:
            raise exceptions.InvalidEndpointsException()
        except keystone_exceptions.AuthorizationFailure:
            raise exceptions.HostUnreachableException(
                url=self.endpoint.auth_url)
        return client

    def _get_auth_info(self, user_key="username",
                       password_key="password",
                       auth_url_key="auth_url",
                       project_name_key="project_id"
                       ):
        kw = {
            user_key: self.endpoint.username,
            password_key: self.endpoint.password,
            auth_url_key: self.endpoint.auth_url
        }
        if project_name_key:
            kw.update({project_name_key: self.endpoint.tenant_name})
        return kw

    @cached
    def nova(self, version="2"):
        """Return nova client."""
        from novaclient import client as nova
        kc = self.keystone()
        compute_api_url = kc.service_catalog.url_for(
            service_type="compute",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        client = nova.Client(version,
                             auth_token=kc.auth_token,
                             http_log_debug=logging.is_debug(),
                             timeout=CONF.openstack_client_http_timeout,
                             insecure=self.endpoint.insecure,
                             cacert=self.endpoint.cacert,
                             **self._get_auth_info(password_key="api_key"))
        client.set_management_url(compute_api_url)
        return client

    @cached
    def neutron(self, version="2.0"):
        """Return neutron client."""
        from neutronclient.neutron import client as neutron
        kc = self.keystone()
        network_api_url = kc.service_catalog.url_for(
            service_type="network",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        client = neutron.Client(version,
                                token=kc.auth_token,
                                endpoint_url=network_api_url,
                                timeout=CONF.openstack_client_http_timeout,
                                insecure=self.endpoint.insecure,
                                ca_cert=self.endpoint.cacert,
                                **self._get_auth_info(
                                    project_name_key="tenant_name")
                                )
        return client

    @cached
    def glance(self, version="1"):
        """Return glance client."""
        import glanceclient as glance
        kc = self.keystone()
        image_api_url = kc.service_catalog.url_for(
            service_type="image",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        client = glance.Client(version,
                               endpoint=image_api_url,
                               token=kc.auth_token,
                               timeout=CONF.openstack_client_http_timeout,
                               insecure=self.endpoint.insecure,
                               cacert=self.endpoint.cacert)
        return client

    @cached
    def heat(self, version="1"):
        """Return heat client."""
        from heatclient import client as heat
        kc = self.keystone()
        orchestration_api_url = kc.service_catalog.url_for(
            service_type="orchestration",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        client = heat.Client(version,
                             endpoint=orchestration_api_url,
                             token=kc.auth_token,
                             timeout=CONF.openstack_client_http_timeout,
                             insecure=self.endpoint.insecure,
                             cacert=self.endpoint.cacert,
                             **self._get_auth_info(project_name_key=None))
        return client

    @cached
    def cinder(self, version="1"):
        """Return cinder client."""
        from cinderclient import client as cinder
        client = cinder.Client(version,
                               http_log_debug=logging.is_debug(),
                               timeout=CONF.openstack_client_http_timeout,
                               insecure=self.endpoint.insecure,
                               cacert=self.endpoint.cacert,
                               **self._get_auth_info(password_key="api_key"))
        kc = self.keystone()
        volume_api_url = kc.service_catalog.url_for(
            service_type="volume",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        client.client.management_url = volume_api_url
        client.client.auth_token = kc.auth_token
        return client

    @cached
    def manila(self, version="1"):
        """Return manila client."""
        from manilaclient import client as manila
        manila_client = manila.Client(
            version,
            region_name=self.endpoint.region_name,
            http_log_debug=logging.is_debug(),
            timeout=CONF.openstack_client_http_timeout,
            insecure=self.endpoint.insecure,
            cacert=self.endpoint.cacert,
            **self._get_auth_info(password_key="api_key",
                                  project_name_key="project_name"))
        kc = self.keystone()
        manila_client.client.management_url = kc.service_catalog.url_for(
            service_type="share",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        manila_client.client.auth_token = kc.auth_token
        return manila_client

    @cached
    def ceilometer(self, version="2"):
        """Return ceilometer client."""
        from ceilometerclient import client as ceilometer
        kc = self.keystone()
        metering_api_url = kc.service_catalog.url_for(
            service_type="metering",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        auth_token = kc.auth_token
        if not hasattr(auth_token, "__call__"):
            # python-ceilometerclient requires auth_token to be a callable
            auth_token = lambda: kc.auth_token

        client = ceilometer.get_client(
            version,
            os_endpoint=metering_api_url,
            token=auth_token,
            timeout=CONF.openstack_client_http_timeout,
            insecure=self.endpoint.insecure,
            cacert=self.endpoint.cacert,
            **self._get_auth_info(project_name_key="tenant_name"))
        return client

    @cached
    def ironic(self, version="1.0"):
        """Return Ironic client."""
        from ironicclient import client as ironic
        kc = self.keystone()
        baremetal_api_url = kc.service_catalog.url_for(
            service_type="baremetal",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        client = ironic.get_client(version,
                                   os_auth_token=kc.auth_token,
                                   ironic_url=baremetal_api_url,
                                   timeout=CONF.openstack_client_http_timeout,
                                   insecure=self.endpoint.insecure,
                                   cacert=self.endpoint.cacert)
        return client

    @cached
    def sahara(self, version="1.1"):
        """Return Sahara client."""
        from saharaclient import client as sahara
        client = sahara.Client(version,
                               **self._get_auth_info(
                                   password_key="api_key",
                                   project_name_key="project_name"))

        return client

    @cached
    def zaqar(self, version=1.1):
        """Return Zaqar client."""
        from zaqarclient.queues import client as zaqar
        kc = self.keystone()
        messaging_api_url = kc.service_catalog.url_for(
            service_type="messaging",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        conf = {"auth_opts": {"backend": "keystone", "options": {
            "os_username": self.endpoint.username,
            "os_password": self.endpoint.password,
            "os_project_name": self.endpoint.tenant_name,
            "os_project_id": kc.auth_tenant_id,
            "os_auth_url": self.endpoint.auth_url,
            "insecure": self.endpoint.insecure,
        }}}
        client = zaqar.Client(url=messaging_api_url,
                              version=version,
                              conf=conf)
        return client

    @cached
    def murano(self, version="1"):
        """Return Murano client."""
        from muranoclient import client as murano
        kc = self.keystone()
        murano_url = kc.service_catalog.url_for(
            service_type=consts.ServiceType.APPLICATION_CATALOG,
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name
        )

        client = murano.Client(version, endpoint=murano_url,
                               token=kc.auth_token)

        return client

    @cached
    def designate(self):
        """Return designate client."""
        from designateclient import v1 as designate
        kc = self.keystone()
        dns_api_url = kc.service_catalog.url_for(
            service_type="dns",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        client = designate.Client(
            endpoint=dns_api_url,
            token=kc.auth_token,
            insecure=self.endpoint.insecure)
        return client

    @cached
    def trove(self, version="1.0"):
        """Returns trove client."""
        from troveclient import client as trove
        client = trove.Client(version,
                              region_name=self.endpoint.region_name,
                              timeout=CONF.openstack_client_http_timeout,
                              insecure=self.endpoint.insecure,
                              cacert=self.endpoint.cacert,
                              **self._get_auth_info(password_key="api_key")
                              )
        return client

    @cached
    def mistral(self):
        """Return Mistral client."""
        from mistralclient.api import client
        kc = self.keystone()

        mistral_url = kc.service_catalog.url_for(
            service_type="workflowv2",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)

        client = client.client(mistral_url=mistral_url,
                               service_type="workflowv2",
                               auth_token=kc.auth_token)
        return client

    @cached
    def swift(self):
        """Return swift client."""
        from swiftclient import client as swift
        kc = self.keystone()
        object_api_url = kc.service_catalog.url_for(
            service_type="object-store",
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        client = swift.Connection(retries=1,
                                  preauthurl=object_api_url,
                                  preauthtoken=kc.auth_token,
                                  insecure=self.endpoint.insecure,
                                  cacert=self.endpoint.cacert,
                                  **self._get_auth_info(
                                      user_key="user",
                                      password_key="key",
                                      auth_url_key="authurl",
                                      project_name_key="tenant_name")
                                  )
        return client

    @cached
    def ec2(self):
        """Return ec2 client."""
        import boto
        kc = self.keystone()
        if kc.version != "v2.0":
            raise exceptions.RallyException(
                _("Rally EC2 benchmark currently supports only"
                  "Keystone version 2"))
        ec2_credential = kc.ec2.create(user_id=kc.auth_user_id,
                                       tenant_id=kc.auth_tenant_id)
        ec2_api_url = kc.service_catalog.url_for(
            service_type=consts.ServiceType.EC2,
            endpoint_type=self.endpoint.endpoint_type,
            region_name=self.endpoint.region_name)
        client = boto.connect_ec2_endpoint(
            url=ec2_api_url,
            aws_access_key_id=ec2_credential.access,
            aws_secret_access_key=ec2_credential.secret,
            is_secure=self.endpoint.insecure)
        return client

    @cached
    def services(self):
        """Return available services names and types.

        :returns: dict, {"service_type": "service_name", ...}
        """
        services_data = {}
        available_services = self.keystone().service_catalog.get_endpoints()
        for service_type in available_services.keys():
            if service_type in consts.ServiceType:
                services_data[service_type] = consts.ServiceType[service_type]
        return services_data

    @classmethod
    def register(cls, client_name):
        """Decorator that adds new OpenStack client dynamically.

        :param client_name: str name how client will be named in Rally clients

        Decorated function will be added to Clients in runtime, so its sole
        argument is a Clients instance.

        Example:
          >>> from rally import osclients
          >>> @osclients.Clients.register("supernova")
          ... def another_nova_client(self):
          ...   from novaclient import client as nova
          ...   return nova.Client("2", auth_token=self.keystone().auth_token,
          ...                      **self._get_auth_info(password_key="key"))
          ...
          >>> clients = osclients.Clients.create_from_env()
          >>> clients.supernova().services.list()[:2]
          [<Service: nova-conductor>, <Service: nova-cert>]
        """
        def wrap(client_func):
            if hasattr(cls, client_name):
                raise ValueError(
                    _("Can not register client: name already exists: %s")
                    % client_name)
            setattr(cls, client_name, cached(client_func))
            return client_func

        return wrap
