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
from rally.common import utils as rutils
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
                      "creation.")
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(GLANCE_BENCHMARK_OPTS, group=benchmark_group)


@six.add_metaclass(abc.ABCMeta)
class GlanceWrapper(object):
    def __init__(self, client, owner):
        self.owner = owner
        self.client = client

    def get_image(self, image):
        """Gets image.

        This serves to fetch the latest data on the image for the
        various wait_for_*() functions.

        Must raise rally.exceptions.GetResourceNotFound if the
        resource is not found or deleted.
        """
        # NOTE(stpierre): This function actually has a single
        # implementation that works for both Glance v1 and Glance v2,
        # but since we need to use this function in both wrappers, it
        # gets implemented here.
        try:
            return self.client.images.get(image.id)
        except glance_exc.HTTPNotFound:
            raise exceptions.GetResourceNotFound(resource=image)

    @abc.abstractmethod
    def create_image(self, container_format, image_location, disk_format):
        """Creates new image.

        Accepts all Glance v2 parameters.
        """

    @abc.abstractmethod
    def set_visibility(self, image, visibility="public"):
        """Set an existing image to public or private."""

    @abc.abstractmethod
    def list_images(self, **filters):
        """List images.

        Accepts all Glance v2 filters.
        """


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
        if "visibility" in kw:
            kw["is_public"] = kw.pop("visibility") == "public"

        image_location = os.path.expanduser(image_location)

        try:
            if os.path.isfile(image_location):
                kw["data"] = open(image_location)
            else:
                kw["copy_from"] = image_location

            image = self.client.images.create(**kw)

            rutils.interruptable_sleep(CONF.benchmark.
                                       glance_image_create_prepoll_delay)

            image = utils.wait_for_status(
                image, ["active"],
                update_resource=self.get_image,
                timeout=CONF.benchmark.glance_image_create_timeout,
                check_interval=CONF.benchmark.
                glance_image_create_poll_interval)
        finally:
            if "data" in kw:
                kw["data"].close()

        return image

    def set_visibility(self, image, visibility="public"):
        self.client.images.update(image.id, is_public=(visibility == "public"))

    def list_images(self, **filters):
        kwargs = {"filters": filters}
        if "owner" in filters:
            # NOTE(stpierre): in glance v1, "owner" is not a filter,
            # so we need to handle it separately.
            kwargs["owner"] = kwargs["filters"].pop("owner")
        visibility = kwargs["filters"].pop("visibility", None)
        images = self.client.images.list(**kwargs)
        # NOTE(stpierre): Glance v1 isn't smart enough to filter on
        # public/private images, so we have to do it manually.
        if visibility is not None:
            is_public = visibility == "public"
            return [i for i in images if i.is_public is is_public]
        return images


class GlanceV2Wrapper(GlanceWrapper):
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

        rutils.interruptable_sleep(CONF.benchmark.
                                   glance_image_create_prepoll_delay)

        start = time.time()
        image = utils.wait_for_status(
            image, ["queued"],
            update_resource=self.get_image,
            timeout=CONF.benchmark.glance_image_create_timeout,
            check_interval=CONF.benchmark.
            glance_image_create_poll_interval)
        timeout = time.time() - start

        image_data = None
        response = None
        try:
            if os.path.isfile(image_location):
                image_data = open(image_location)
            else:
                response = requests.get(image_location, stream=True)
                image_data = response.raw
            self.client.images.upload(image.id, image_data)
        finally:
            if image_data is not None:
                image_data.close()
            if response is not None:
                response.close()

        return utils.wait_for_status(
            image, ["active"],
            update_resource=self.get_image,
            timeout=timeout,
            check_interval=CONF.benchmark.
            glance_image_create_poll_interval)

    def set_visibility(self, image, visibility="public"):
        self.client.images.update(image.id, visibility=visibility)

    def list_images(self, **filters):
        return self.client.images.list(filters=filters)


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
