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

import uuid

from glanceclient import exc as glance_exc
import mock

from rally import exceptions
from rally.plugins.openstack import service
from rally.plugins.openstack.services.image import glance_common
from rally.plugins.openstack.services.image import image
from tests.unit import test


class FullGlance(service.Service, glance_common.GlanceMixin):
    """Implementation of GlanceMixin with Service base class."""
    pass


class GlanceMixinTestCase(test.TestCase):
    def setUp(self):
        super(GlanceMixinTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.glance = self.clients.glance.return_value
        self.name_generator = mock.MagicMock()
        self.version = "some"
        self.service = FullGlance(
            clients=self.clients, name_generator=self.name_generator)
        self.service.version = self.version

    def test__get_client(self):
        self.assertEqual(self.glance,
                         self.service._get_client())

    def test_get_image(self):
        image = "image_id"
        self.assertEqual(self.glance.images.get.return_value,
                         self.service.get_image(image))
        self.glance.images.get.assert_called_once_with(image)

    def test_get_image_exception(self):
        image_id = "image_id"
        self.glance.images.get.side_effect = glance_exc.HTTPNotFound

        self.assertRaises(exceptions.GetResourceNotFound,
                          self.service.get_image, image_id)

    def test_delete_image(self):
        image = "image_id"
        self.service.delete_image(image)
        self.glance.images.delete.assert_called_once_with(image)

    def test_download_image(self):
        image_id = "image_id"
        self.service.download_image(image_id)
        self.glance.images.data.assert_called_once_with(image_id,
                                                        do_checksum=True)


class FullUnifiedGlance(glance_common.UnifiedGlanceMixin,
                        service.Service):
    """Implementation of UnifiedGlanceMixin with Service base class."""
    pass


class UnifiedGlanceMixinTestCase(test.TestCase):
    def setUp(self):
        super(UnifiedGlanceMixinTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.name_generator = mock.MagicMock()
        self.impl = mock.MagicMock()
        self.version = "some"
        self.service = FullUnifiedGlance(
            clients=self.clients, name_generator=self.name_generator)
        self.service._impl = self.impl
        self.service.version = self.version

    def test__unify_image(self):
        class Image(object):
            def __init__(self, visibility=None, is_public=None, status=None):
                self.id = uuid.uuid4()
                self.name = str(uuid.uuid4())
                self.visibility = visibility
                self.is_public = is_public
                self.status = status

        visibility = "private"
        image_obj = Image(visibility=visibility)
        unified_image = self.service._unify_image(image_obj)
        self.assertIsInstance(unified_image, image.UnifiedImage)
        self.assertEqual(image_obj.id, unified_image.id)
        self.assertEqual(image_obj.visibility, unified_image.visibility)

        image_obj = Image(is_public="public")
        del image_obj.visibility
        unified_image = self.service._unify_image(image_obj)
        self.assertEqual(image_obj.id, unified_image.id)
        self.assertEqual(image_obj.is_public, unified_image.visibility)

    def test_get_image(self):
        image_id = "image_id"
        self.service.get_image(image=image_id)
        self.service._impl.get_image.assert_called_once_with(image=image_id)

    def test_delete_image(self):
        image_id = "image_id"
        self.service.delete_image(image_id)
        self.service._impl.delete_image.assert_called_once_with(
            image_id=image_id)

    def test_download_image(self):
        image_id = "image_id"
        self.service.download_image(image_id)
        self.service._impl.download_image.assert_called_once_with(
            image_id, do_checksum=True)
