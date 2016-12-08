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

import mock

from rally import exceptions
from rally.task import atomic
from rally.task import service
from tests.unit import test


PATH = "rally.task.service"


class ServiceTestCase(test.TestCase):
    def setUp(self):
        super(ServiceTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.clients.cc.choose_version.return_value = 1

    @mock.patch("%s.atomic" % PATH)
    def test_atomic(self, mock_atomic):
        @service.service("some_service", "some_type", version="1")
        class SomeV1Service(service.Service):
            pass

        SomeV1Service(mock.MagicMock(), atomic_inst=mock.MagicMock())
        self.assertFalse(mock_atomic.ActionTimerMixin.called)

        # ensure that previous call will no affect anything
        mock_atomic.ActionTimerMixin.reset_mock()

        SomeV1Service(mock.MagicMock())
        self.assertTrue(mock_atomic.ActionTimerMixin.called)

    def test_generate_random_name(self):
        @service.service("some_service", "some_type", version="1")
        class SomeV1Service(service.Service):
            pass

        self.assertRaises(exceptions.RallyException,
                          SomeV1Service(self.clients).generate_random_name)

        name_generator = mock.MagicMock()
        impl = SomeV1Service(self.clients, name_generator=name_generator)
        self.assertEqual(name_generator.return_value,
                         impl.generate_random_name())
        name_generator.assert_called_once_with()

    def test_version(self):
        class SomeService(service.UnifiedService):
            pass

        @service.service("some_service", "some_type", version="1")
        class SomeV1Service(service.Service):
            pass

        @service.compat_layer(SomeV1Service)
        class UnifiedSomeV1Service(SomeService):
            pass

        clients = mock.MagicMock()
        clients.some_service.choose_version.return_value = "1"

        self.assertEqual("1", SomeService(clients).version)
        self.assertEqual("1", SomeV1Service(clients).version)
        self.assertEqual("1", UnifiedSomeV1Service(clients).version)

    def test_is_applicable(self):
        class SomeService(service.UnifiedService):
            pass

        @service.service("some_service", "some_type", version="1")
        class SomeV1Service(service.Service):
            pass

        @service.compat_layer(SomeV1Service)
        class UnifiedSomeV1Service(SomeService):
            pass

        clients = mock.MagicMock()
        clients.some_service.choose_version.return_value = "1"

        self.assertFalse(SomeService.is_applicable(clients))
        self.assertTrue(UnifiedSomeV1Service.is_applicable(clients))

        clients.some_service.choose_version.return_value = "2"
        self.assertFalse(SomeService.is_applicable(clients))
        self.assertFalse(UnifiedSomeV1Service.is_applicable(clients))


class ServiceMetaTestCase(test.TestCase):
    def test_servicemeta_fail_on_missed_public_function(self):
        def init_classes():
            class SomeService(service.UnifiedService):
                @service.should_be_overridden
                def foo(self):
                    pass

            @service.service("some_service", "some_type", version="1")
            class SomeV1Service(service.Service):
                pass

            @service.compat_layer(SomeV1Service)
            class UnifiedSomeV1Service(SomeService):
                pass

        e = self.assertRaises(exceptions.RallyException, init_classes)
        self.assertIn("Missed method(s): foo", str(e))


class DiscoverTestCase(test.TestCase):
    def test_discover_impl_based_on_version(self):
        class SomeService(service.UnifiedService):
            pass

        @service.service("some_service", "some_type", version="1")
        class SomeV1Service(service.Service):
            pass

        @service.compat_layer(SomeV1Service)
        class UnifiedSomeV1Service(SomeService):
            pass

        @service.service("some_service", "some_type", version="2")
        class SomeV2Service(service.Service):
            pass

        @service.compat_layer(SomeV2Service)
        class UnifiedSomeV2Service(SomeService):
            pass

        clients = mock.MagicMock()
        clients.some_service.choose_version.return_value = "1"
        self.assertIsInstance(SomeService(clients)._impl, UnifiedSomeV1Service)

        clients.some_service.choose_version.return_value = "2"
        self.assertIsInstance(SomeService(clients)._impl, UnifiedSomeV2Service)

        self.assertFalse(clients.services.called)

    def test_discover_impl_based_on_service(self):
        class SomeService(service.UnifiedService):
            pass

        @service.service("some_service", "some_type", version="1")
        class SomeV1Service(service.Service):
            pass

        @service.compat_layer(SomeV1Service)
        class UnifiedSomeV1Service(SomeService):
            pass

        @service.service("another_impl_of_some_service", "another_type",
                         version="2")
        class AnotherSomeV2Service(service.Service):
            pass

        @service.compat_layer(AnotherSomeV2Service)
        class UnifiedAnotherSomeV2Service(SomeService):
            pass

        clients = mock.MagicMock()
        clients.some_service.choose_version.return_value = "1"
        clients.another_impl_of_some_service.choose_version.return_value = "2"

        clients.services.return_value = {"some_type": "some_service"}
        self.assertIsInstance(SomeService(clients)._impl, UnifiedSomeV1Service)

        clients.services.return_value = {
            "another_type": "another_impl_of_some_service"}
        self.assertIsInstance(SomeService(clients)._impl,
                              UnifiedAnotherSomeV2Service)

    def test_discover_impl_fail_with_wrong_version(self):

        class SomeService(service.UnifiedService):
            pass

        @service.service("some_service", "some_type", version="1")
        class SomeV1Service(service.Service):
            pass

        @service.compat_layer(SomeV1Service)
        class UnifiedSomeV1Service(SomeService):
            pass

        clients = mock.MagicMock()
        clients.some_service.choose_version.return_value = "2"

        e = self.assertRaises(exceptions.RallyException, SomeService, clients)
        self.assertEqual("There is no proper implementation for "
                         "SomeService.", str(e))

    def test_discover_impl_fail_with_unavailable_service(self):

        class SomeService(service.UnifiedService):
            pass

        @service.service("some_service", "some_type", version="1")
        class SomeV1Service(SomeService):
            pass

        @service.compat_layer(SomeV1Service)
        class UnifiedSomeV1Service(SomeService):
            pass

        @service.service("another_service", "another_type", version="2")
        class AnotherSomeV2Service(SomeService):
            pass

        @service.compat_layer(AnotherSomeV2Service)
        class UnifiedAnotherSomeV2Service(SomeService):
            pass

        clients = mock.MagicMock()
        clients.some_service.choose_version.return_value = "1"
        clients.another_service.choose_version.return_value = "2"
        clients.services.return_value = {}

        e = self.assertRaises(exceptions.RallyException, SomeService, clients)
        self.assertEqual("There is no proper implementation for SomeService.",
                         str(e))


class MethodWrapperTestCase(test.TestCase):
    def test_positional(self):
        class Some(object):
            @service.method_wrapper
            def foo(slf, *args, **kwargs):
                if len(args) > 1:
                    self.fail("`method_wrapper` should fail when number of "
                              "positional arguments are bigger than 1.")

        Some().foo()
        Some().foo(some=2, another=3)
        Some().foo(1, some=2, another=3)
        self.assertRaises(TypeError, Some().foo, 1, 2)

    def test_disabling_atomics(self):
        class Some(service.UnifiedService):

            def discover_impl(self):
                return mock.MagicMock, None

            @atomic.action_timer("some")
            def foo(slf):
                pass

            def bar(slf):
                pass

        some = Some(mock.MagicMock(version="777"))
        some.foo(no_atomic=True)
        self.assertNotIn("some", some._atomic_actions)
        # check that we are working with correct variable
        some.foo()
        self.assertIn("some", some._atomic_actions)


class ServiceWithoutAtomicTestCase(test.TestCase):
    def test_access(self):
        class Some(atomic.ActionTimerMixin):
            def __getattr__(self, attr):
                return self

        some_cls = Some()
        # add something to atomic actions dict to simplify comparison
        # (empty fake dict != not empty _atomic_actions dict)
        with atomic.ActionTimer(some_cls, "some"):
            pass
        wrapped_service = service._ServiceWithoutAtomic(some_cls)
        self.assertNotEqual(some_cls.atomic_actions(),
                            wrapped_service.atomic_actions())
        self.assertNotEqual(some_cls._atomic_actions,
                            wrapped_service._atomic_actions)
        self.assertEqual(some_cls, wrapped_service.some_var)
