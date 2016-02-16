# Copyright 2016: Mirantis Inc.
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
import os
import time

from rally.common import logging
from rally import exceptions
from rally.task import utils

from glanceclient import exc as glance_exc
from oslo_config import cfg
import requests
import six

LOG = logging.getLogger(__name__)

GLANCE_BENCHMARK_OPTS = [
    cfg.FloatOpt("glance_image_create_prepoll_delay",
                 default=2.0,
                 help="Time to sleep after creating a resource before "
                      "polling for it status"),
    cfg.FloatOpt("glance_image_create_timeout",
                 default=120.0,
                 help="Time to wait for glance image to be created."),
    cfg.FloatOpt("glance_image_create_poll_interval",
                 default=1.0,
                 help="Interval between checks when waiting for image "
                      "creation."),
    cfg.FloatOpt("glance_image_delete_timeout",
                 default=120.0,
                 help="Time to wait for glance image to be deleted."),
    cfg.FloatOpt("glance_image_delete_poll_interval",
                 default=1.0,
                 help="Interval between checks when waiting for image "
                      "deletion.")
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(GLANCE_BENCHMARK_OPTS, group=benchmark_group)


@six.add_metaclass(abc.ABCMeta)
class GlanceWrapper(object):
    def __init__(self, client, owner):
        self.owner = owner
        self.client = client

    @abc.abstractmethod
    def create_image(self, container_format, image_location, disk_format):
        """Creates new image."""

    @abc.abstractmethod
    def delete_image(self, image):
        """Deletes image."""


class GlanceV1Wrapper(GlanceWrapper):
    def create_image(self, container_format, image_location,
                     disk_format, **kwargs):
        kw = {
            "container_format": container_format,
            "disk_format": disk_format,
        }
        kw.update(kwargs)
        if "name" not in kw:
            kw["name"] = self.owner.generate_random_name()
        image_location = os.path.expanduser(image_location)

        try:
            if os.path.isfile(image_location):
                kw["data"] = open(image_location)
            else:
                kw["copy_from"] = image_location

            image = self.client.images.create(**kw)

            time.sleep(CONF.benchmark.glance_image_create_prepoll_delay)

            image = utils.wait_for_status(
                image, ["active"],
                update_resource=utils.get_from_manager(),
                timeout=CONF.benchmark.glance_image_create_timeout,
                check_interval=CONF.benchmark.
                glance_image_create_poll_interval)
        finally:
            if "data" in kw:
                kw["data"].close()

        return image

    def delete_image(self, image):
        image.delete()
        utils.wait_for_status(
            image, ["deleted"],
            check_deletion=True,
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.glance_image_delete_timeout,
            check_interval=CONF.benchmark.glance_image_delete_poll_interval)


class GlanceV2Wrapper(GlanceWrapper):
    def _get_image(self, image):
        try:
            return self.client.images.get(image.id)
        except glance_exc.HTTPNotFound:
            raise exceptions.GetResourceNotFound(resource=image)

    def create_image(self, container_format, image_location,
                     disk_format, **kwargs):
        kw = {
            "container_format": container_format,
            "disk_format": disk_format,
        }
        kw.update(kwargs)
        if "name" not in kw:
            kw["name"] = self.owner.generate_random_name()

        image_location = os.path.expanduser(image_location)

        image = self.client.images.create(**kw)

        time.sleep(CONF.benchmark.glance_image_create_prepoll_delay)

        start = time.time()
        image = utils.wait_for_status(
            image, ["queued"],
            update_resource=self._get_image,
            timeout=CONF.benchmark.glance_image_create_timeout,
            check_interval=CONF.benchmark.
            glance_image_create_poll_interval)
        timeout = time.time() - start

        image_data = None
        try:
            if os.path.isfile(image_location):
                image_data = open(image_location)
            else:
                response = requests.get(image_location)
                image_data = response.raw
            self.client.images.upload(image.id, image_data)
        finally:
            if image_data is not None:
                image_data.close()

        return utils.wait_for_status(
            image, ["active"],
            update_resource=self._get_image,
            timeout=timeout,
            check_interval=CONF.benchmark.
            glance_image_create_poll_interval)

    def delete_image(self, image):
        self.client.images.delete(image.id)
        utils.wait_for_status(
            image, ["deleted"],
            check_deletion=True,
            update_resource=self._get_image,
            timeout=CONF.benchmark.glance_image_delete_timeout,
            check_interval=CONF.benchmark.glance_image_delete_poll_interval)


def wrap(client, owner):
    """Returns glanceclient wrapper based on glance client version."""
    version = client.choose_version()
    if version == "1":
        return GlanceV1Wrapper(client(), owner)
    elif version == "2":
        return GlanceV2Wrapper(client(), owner)
    else:
        msg = "Version %s of the glance API could not be identified." % version
        LOG.warning(msg)
        raise exceptions.InvalidArgumentsException(msg)
