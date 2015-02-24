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

import logging

import mock

from rally.common import log
from tests.unit import test


class LogTestCase(test.TestCase):

    @mock.patch("rally.common.log.CONF")
    @mock.patch("rally.common.log.handlers")
    @mock.patch("rally.common.log.oslogging")
    def test_setup(self, mock_oslogger, mock_handlers, mock_conf):

        proj = "fakep"
        version = "fakev"
        mock_handlers.ColorHandler.LEVEL_COLORS = {
            logging.DEBUG: "debug_color"}
        mock_conf.rally_debug = True

        log.setup(proj, version)

        self.assertIn(logging.RDEBUG, mock_handlers.ColorHandler.LEVEL_COLORS)
        self.assertEqual(
            mock_handlers.ColorHandler.LEVEL_COLORS[logging.DEBUG],
            mock_handlers.ColorHandler.LEVEL_COLORS[logging.RDEBUG])

        mock_oslogger.setup.assert_called_once_with(mock_conf, proj, version)
        mock_oslogger.getLogger(None).logger.setLevel.assert_called_once_with(
            logging.RDEBUG)

    @mock.patch("rally.common.log.logging")
    @mock.patch("rally.common.log.RallyContextAdapter")
    @mock.patch("rally.common.log.oslogging")
    def test_getLogger(self, mock_oslogger, mock_radapter, mock_pylogging):

        name = "fake"
        vers = "fake"
        mock_oslogger._loggers = dict()

        returned_logger = log.getLogger(name, vers)

        self.assertIn(name, mock_oslogger._loggers)
        mock_radapter.assert_called_once_with(
            mock_pylogging.getLogger(name),
            {"project": "rally", "version": vers})
        self.assertEqual(mock_oslogger._loggers[name], returned_logger)


class LogRallyContaxtAdapter(test.TestCase):

    @mock.patch("rally.common.log.logging")
    @mock.patch("rally.common.log.oslogging.KeywordArgumentAdapter")
    def test_debug(self, mock_oslo_adapter, mock_logging):

        mock_logging.RDEBUG = 123
        fake_msg = "fake message"
        radapter = log.RallyContextAdapter(mock.MagicMock(), "fakep")
        radapter.log = mock.MagicMock()

        radapter.debug(fake_msg)

        radapter.log.assert_called_once_with(mock_logging.RDEBUG,
                                             fake_msg)


class ExceptionLoggerTestCase(test.TestCase):

    @mock.patch("rally.common.log.is_debug")
    def test_context(self, mock_is_debug):
        # Prepare
        mock_is_debug.return_value = True

        logger = mock.MagicMock()
        exception = Exception()

        # Run
        with log.ExceptionLogger(logger, "foo") as e:
            raise exception

        # Assertions
        logger.warning.assert_called_once_with("foo")

        logger.exception.assert_called_once_with(exception)

        logger.debug.assert_called_once_with(exception)

        self.assertEqual(e.exception, exception)
