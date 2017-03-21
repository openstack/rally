# Copyright 2017: Mirantis Inc.
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

import jsonschema

from rally.deployment import credential
from tests.unit import test


@credential.configure("foo")
class FooCredential(credential.Credential):
    def __init__(self, bar=None):
        self.bar = bar

    def to_dict(self):
        return {"bar": self.bar}

    def verify_connection(self):
        pass

    def list_services(self):
        return {"foo": "foo-type"}


class CredentialTestCase(test.TestCase):

    def setUp(self):
        super(CredentialTestCase, self).setUp()
        self.cred_cls = credential.get("foo")

    def test_configure_and_get(self):
        self.assertIs(FooCredential, self.cred_cls)

    def test_foo_credential(self):
        cred = self.cred_cls(bar=42)
        cred.verify_connection()
        self.assertEqual({"bar": 42}, cred.to_dict())
        self.assertEqual({"foo": "foo-type"}, cred.list_services())


@credential.configure_builder("foo")
class FooCredentialBuilder(credential.CredentialBuilder):

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "bar": {"type": "integer"}
        },
        "required": ["bar"],
        "additionalProperties": False
    }

    def build_credentials(self):
        return {"admin": {"bar": self.config["bar"]}, "users": []}


class CredentialBuilderTestCase(test.TestCase):

    def setUp(self):
        super(CredentialBuilderTestCase, self).setUp()
        self.cred_builder_cls = credential.get_builder("foo")

    def test_configure_and_get(self):
        self.assertIs(FooCredentialBuilder, self.cred_builder_cls)

    def test_validate(self):
        self.cred_builder_cls.validate({"bar": 42})

    def test_validate_error(self):
        self.assertRaises(jsonschema.ValidationError,
                          self.cred_builder_cls.validate,
                          {"bar": "spam"})
