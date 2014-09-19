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

import mock
from oslo.config import cfg
from oslotest import mockpatch

from rally.benchmark.scenarios.cinder import utils
from tests import test

BM_UTILS = 'rally.benchmark.utils'
CINDER_UTILS = "rally.benchmark.scenarios.cinder.utils"


class CinderScenarioTestCase(test.TestCase):

    def setUp(self):
        super(CinderScenarioTestCase, self).setUp()
        self.res_is = mockpatch.Patch(BM_UTILS + ".resource_is")
        self.get_fm = mockpatch.Patch(BM_UTILS + '.get_from_manager')
        self.wait_for = mockpatch.Patch(CINDER_UTILS + ".bench_utils.wait_for")
        self.wait_for_delete = mockpatch.Patch(
            CINDER_UTILS + ".bench_utils.wait_for_delete")
        self.useFixture(self.wait_for)
        self.useFixture(self.wait_for_delete)
        self.useFixture(self.res_is)
        self.useFixture(self.get_fm)
        self.gfm = self.get_fm.mock
        self.useFixture(mockpatch.Patch('time.sleep'))
        self.scenario = utils.CinderScenario()

    def _test_atomic_action_timer(self, atomic_actions, name):
        action_duration = atomic_actions.get(name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(CINDER_UTILS + '.CinderScenario.clients')
    def test__list_volumes(self, mock_clients):
        volumes_list = mock.Mock()
        mock_clients("cinder").volumes.list.return_value = volumes_list
        return_volumes_list = self.scenario._list_volumes()
        self.assertEqual(volumes_list, return_volumes_list)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       'cinder.list_volumes')

    @mock.patch(CINDER_UTILS + '.CinderScenario.clients')
    def test__create_volume(self, mock_clients):
        CONF = cfg.CONF
        volume = mock.Mock()
        mock_clients('cinder').volumes.create.return_value = volume
        return_volume = self.scenario._create_volume(1)
        self.wait_for.mock.assert_called_once_with(
            volume,
            is_ready=self.res_is.mock(),
            update_resource=self.gfm(),
            timeout=CONF.benchmark.cinder_volume_create_timeout,
            check_interval=CONF.benchmark.cinder_volume_create_poll_interval
        )
        self.res_is.mock.assert_has_calls(mock.call('available'))
        self.assertEqual(self.wait_for.mock(), return_volume)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       'cinder.create_volume')

    def test__delete_volume(self):
        cinder = mock.Mock()
        self.scenario._delete_volume(cinder)
        cinder.delete.assert_called_once_with()
        self.wait_for_delete.mock.assert_called_once_with(
            cinder,
            update_resource=self.gfm(),
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       'cinder.delete_volume')

    @mock.patch(CINDER_UTILS + '.CinderScenario.clients')
    def test__create_snapshot(self, mock_clients):
        snapshot = mock.Mock()
        mock_clients("cinder").volume_snapshots.create.return_value = snapshot

        return_snapshot = self.scenario._create_snapshot('uuid', False)

        self.wait_for.mock.assert_called_once_with(
            snapshot,
            is_ready=self.res_is.mock(),
            update_resource=self.gfm(),
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self.res_is.mock.assert_has_calls(mock.call('available'))
        self.assertEqual(self.wait_for.mock(), return_snapshot)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       'cinder.create_snapshot')

    def test__delete_snapshot(self):
        snapshot = mock.Mock()
        self.scenario._delete_snapshot(snapshot)
        snapshot.delete.assert_called_once_with()
        self.wait_for_delete.mock.assert_called_once_with(
            snapshot,
            update_resource=self.gfm(),
            timeout=cfg.CONF.benchmark.cinder_volume_create_timeout,
            check_interval=cfg.CONF.benchmark
            .cinder_volume_create_poll_interval)
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       'cinder.delete_snapshot')
