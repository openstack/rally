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

from rally.common import logging

import openstack
from monascaclient import client

LOG = logging.getLogger(__name__)

# Can we autodetect this
API_VERSION = "2_0"

class MonascaClient(object):
    """The helper class for communication with Monasca"""

    def __init__(self, url):
        # might want to specify cloud and region in the connect call
        conn = openstack.connect()

        services = conn.list_services()

        candidate_services = conn.search_services("monasca-api")

        if not candidate_services:
            print("monasca api not found")

        service = candidate_services[0]

        candidate_endpoints = conn.search_endpoints(
            filters={'service_id': service.id, 'interface': 'public'})

        if not candidate_endpoints:
            print("endpoint now found")

        endpoint = candidate_endpoints[0]

        # export OS_PROJECT=monasca
        project = conn.current_project

        project_id = project.id
        project_domain_id = project.domain_id

        user_id = conn.current_user_id

        candidate_users = conn.search_users(user_id)

        if not candidate_users:
            print("user not found")

        user = candidate_users[0]

        token = conn.authorize()

        # TODO: could we use Resource from openstacksdk to prevent a dependency on monasca client
        c = client.Client(
            api_version=API_VERSION,
            endpoint=endpoint.url,
            token=token,
            project_id=project_id,
            project_domain_id=project_domain_id,
            user_domain_id=user.domain_id,
            auth_url=conn.auth["auth_url"]
        )

        self.client = c

    def post(self, metrics):
        for metric in metrics:
            self.client.metrics.create(jsonbody=metric)