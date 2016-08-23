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

import abc

from rally.common import logging
from rally import exceptions

import six

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class CinderWrapper(object):
    def __init__(self, client, owner):
        self.owner = owner
        self.client = client

    @abc.abstractmethod
    def create_volume(self, volume):
        """Creates new volume."""

    @abc.abstractmethod
    def update_volume(self, volume):
        """Updates name and description for this volume."""

    @abc.abstractmethod
    def create_snapshot(self, volume_id):
        """Creates a volume snapshot."""


class CinderV1Wrapper(CinderWrapper):
    def create_volume(self, size, **kwargs):
        kwargs["display_name"] = self.owner.generate_random_name()
        volume = self.client.volumes.create(size, **kwargs)
        return volume

    def update_volume(self, volume, **update_args):
        update_args["display_name"] = self.owner.generate_random_name()
        update_args["display_description"] = (
            update_args.get("display_description"))
        self.client.volumes.update(volume, **update_args)

    def create_snapshot(self, volume_id, **kwargs):
        kwargs["display_name"] = self.owner.generate_random_name()
        snapshot = self.client.volume_snapshots.create(volume_id, **kwargs)
        return snapshot


class CinderV2Wrapper(CinderWrapper):
    def create_volume(self, size, **kwargs):
        kwargs["name"] = self.owner.generate_random_name()

        volume = self.client.volumes.create(size, **kwargs)
        return volume

    def update_volume(self, volume, **update_args):
        update_args["name"] = self.owner.generate_random_name()
        update_args["description"] = update_args.get("description")
        self.client.volumes.update(volume, **update_args)

    def create_snapshot(self, volume_id, **kwargs):
        kwargs["name"] = self.owner.generate_random_name()
        snapshot = self.client.volume_snapshots.create(volume_id, **kwargs)
        return snapshot


def wrap(client, owner):
    """Returns cinderclient wrapper based on cinder client version."""
    version = client.choose_version()
    if version == "1":
        return CinderV1Wrapper(client(), owner)
    elif version == "2":
        return CinderV2Wrapper(client(), owner)
    else:
        msg = "This version of API %s could not be identified." % version
        LOG.warning(msg)
        raise exceptions.InvalidArgumentsException(msg)
