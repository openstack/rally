# Copyright 2014: Mirantis Inc.
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

import datetime
import os
import time
import urllib2
import urlparse

from oslo.config import cfg
from six.moves import configparser
from six.moves import http_client as httplib

from rally import db
from rally import exceptions
from rally.objects import endpoint
from rally.openstack.common.gettextutils import _
from rally import osclients


image_opts = [
    cfg.StrOpt('cirros_version',
               default='0.3.2',
               help='Version of cirros image'),
    cfg.StrOpt('cirros_image',
               default='cirros-0.3.2-x86_64-disk.img',
               help='Cirros image name'),
]
CONF = cfg.CONF
CONF.register_opts(image_opts, 'image')


class TempestConf(object):

    def __init__(self, deploy_id):
        self.endpoint = db.deployment_get(deploy_id)['endpoints'][0]
        self.clients = osclients.Clients(endpoint.Endpoint(**self.endpoint))
        try:
            self.keystoneclient = self.clients.verified_keystone()
        except exceptions.InvalidAdminException:
            msg = _('Admin permission is required to run tempest. User %s '
                    'doesn\'t have admin role') % self.endpoint['username']
            raise exceptions.TempestConfigCreationFailure(message=msg)
        self.available_services = [service['name'] for service in
                                   self.keystoneclient.
                                   service_catalog.get_data()]
        self.conf = configparser.ConfigParser()
        self.conf.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        self.deploy_id = deploy_id
        self.data_path = os.path.join(os.path.expanduser('~'), '.rally',
                                      'tempest', 'data')
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
        self.img_path = os.path.join(self.data_path,
                                     CONF.image.cirros_image)
        if not os.path.isfile(self.img_path):
            self._load_img()

    def _load_img(self):
        cirros_url = ('http://download.cirros-cloud.net/%s/%s' %
                      (CONF.image.cirros_version,
                       CONF.image.cirros_image))
        try:
            response = urllib2.urlopen(cirros_url)
        except urllib2.URLError as err:
            msg = _('Error on downloading cirros image, possibly'
                    ' no connection to Internet with message %s') % str(err)
            raise exceptions.TempestConfigCreationFailure(message=msg)
        if response.getcode() == httplib.OK:
            with open(self.img_path, 'wb') as img_file:
                img_file.write(response.read())
        else:
            if response.getcode() == httplib.NOT_FOUND:
                msg = _('Error on downloading cirros image, possibly'
                        'invalid cirros_version or cirros_image in rally.conf')
            else:
                msg = _('Error on downloading cirros image, '
                        'HTTP error code %s') % response.getcode()
            raise exceptions.TempestConfigCreationFailure(message=msg)

    def _get_url(self, servicename):
        for service in self.keystoneclient.auth_ref['serviceCatalog']:
            if service['name'] == servicename:
                return service['endpoints'][0]['publicURL']

    def _set_default(self):
        lock_path = os.path.join(self.data_path,
                                 'lock_files_%s' % self.deploy_id)
        if not os.path.exists(lock_path):
            os.makedirs(lock_path)
        self.conf.set('DEFAULT', 'lock_path', lock_path)

    def _set_boto(self):
        self.conf.set('boto', 'ec2_url', self._get_url('ec2'))
        self.conf.set('boto', 's3_url', self._get_url('s3'))
        matherials_path = os.path.join(self.data_path, 's3matherials')
        self.conf.set('boto', 's3_materials_path', matherials_path)
        # TODO(olkonami): find out how can we get ami, ari, aki manifest files

    def _set_compute_images(self):
        glanceclient = self.clients.glance()
        image_list = [img for img in glanceclient.images.list()
                      if img.status.lower() == 'active' and
                      img.name is not None and 'cirros' in img.name]
        # Upload new images if there are no
        # necessary images in the cloud (cirros)
        while len(image_list) < 2:
            now = (datetime.datetime.fromtimestamp(time.time()).
                   strftime('%Y_%m_%d_%H_%M_%S'))
            try:
                image = glanceclient.images.create(name=('cirros_%s' % now),
                                                   disk_format='qcow2',
                                                   container_format='bare')
                image.update(data=open(self.img_path, 'rb'))
                image_list.append(image)
            except Exception as e:
                msg = _('There are no desired images (cirros) or only one and '
                        'new image could not be created.\n'
                        'Reason: %s') % e.message
                raise exceptions.TempestConfigCreationFailure(message=msg)
        self.conf.set('compute', 'image_ref', image_list[0].id)
        self.conf.set('compute', 'image_ref_alt', image_list[1].id)

    def _set_compute_flavors(self):
        novaclient = self.clients.nova()
        flavor_list = sorted(novaclient.flavors.list(),
                             key=lambda flv: flv.ram)
        # Create new flavors if they are missing
        while len(flavor_list) < 2:
            now = (datetime.datetime.fromtimestamp(time.time()).
                   strftime('%Y_%m_%d_%H_%M_%S'))
            try:
                flv = novaclient.flavors.create("m1.tiny_%s" % now, 512, 1, 1)
                flavor_list.append(flv)
            except Exception as e:
                msg = _('There are no desired flavors or only one and '
                        'new flavor could not be created.\n'
                        'Reason: %s') % e.message
                raise exceptions.TempestConfigCreationFailure(message=msg)
        self.conf.set('compute', 'flavor_ref', flavor_list[0].id)
        self.conf.set('compute', 'flavor_ref_alt', flavor_list[1].id)

    def _set_compute_ssh_connect_method(self):
        if 'neutron' in self.available_services:
            self.conf.set('compute', 'ssh_connect_method', 'floating')
        else:
            self.conf.set('compute', 'ssh_connect_method', 'fixed')

    def _set_compute_admin(self):
        self.conf.set('compute-admin', 'username', self.endpoint['username'])
        self.conf.set('compute-admin', 'password', self.endpoint['password'])
        self.conf.set('compute-admin', 'tenant_name',
                      self.endpoint['tenant_name'])

    def _set_identity(self):
        self.conf.set('identity', 'username', self.endpoint['username'])
        self.conf.set('identity', 'password', self.endpoint['password'])
        self.conf.set('identity', 'tenant_name', self.endpoint['tenant_name'])
        self.conf.set('identity', 'admin_username', self.endpoint['username'])
        self.conf.set('identity', 'admin_password', self.endpoint['password'])
        self.conf.set('identity', 'admin_tenant_name',
                      self.endpoint['tenant_name'])
        self.conf.set('identity', 'uri', self.endpoint['auth_url'])
        self.conf.set('identity', 'uri_v3',
                      self.endpoint['auth_url'].replace('/v2.0', '/v3'))

    def _set_network(self):
        if 'neutron' in self.available_services:
            neutron = self.clients.neutron()
            public_net = [net for net in neutron.list_networks()['networks'] if
                          net['status'] == 'ACTIVE' and
                          net['router:external'] is True]
            if public_net:
                net_id = public_net[0]['id']
                self.conf.set('network', 'public_network_id', net_id)
                public_router = neutron.list_routers(
                    network_id=net_id)['routers'][0]
                self.conf.set('network', 'public_router_id',
                              public_router['id'])
                subnet = neutron.list_subnets(network_id=net_id)['subnets'][0]
            else:
                subnet = neutron.list_subnets()[0]
            self.conf.set('network', 'default_network', subnet['cidr'])
        else:
            network = self.clients.nova().networks.list()[0]
            self.conf.set('network', 'default_network', network.cidr)

    def _set_service_available(self):
        services = ['neutron', 'heat', 'ceilometer', 'swift',
                    'cinder', 'nova', 'glance']
        for service in services:
            self.conf.set('service_available', service,
                          str(service in self.available_services))
        horizon_url = ('http://' +
                       urlparse.urlparse(self.endpoint['auth_url']).hostname)
        answer_code = urllib2.urlopen(horizon_url).getcode()
        # convert boolean to string because ConfigParser fails
        # on attempt to get option with boolean value
        self.conf.set('service_available', 'horizon',
                      str(answer_code == httplib.OK))

    def generate(self):
        self._set_default()
        self._set_boto()
        self._set_compute_images()
        self._set_compute_flavors()
        self._set_compute_admin()
        self._set_identity()
        self._set_network()
        self._set_service_available()
        return self.conf
