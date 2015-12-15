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

from rally.common import logging as log
from tests.unit import test


class LogTestCase(test.TestCase):

    @mock.patch("rally.common.logging.CONF")
    @mock.patch("rally.common.logging.handlers")
    @mock.patch("rally.common.logging.oslogging")
    def test_setup(self, mock_oslogging, mock_handlers, mock_conf):

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

        mock_oslogging.setup.assert_called_once_with(mock_conf, proj, version)
        mock_oslogging.getLogger(None).logger.setLevel.assert_called_once_with(
            logging.RDEBUG)

    @mock.patch("rally.common.logging.log")
    @mock.patch("rally.common.logging.RallyContextAdapter")
    @mock.patch("rally.common.logging.oslogging")
    def test_getLogger(self, mock_oslogging, mock_rally_context_adapter,
                       mock_log):

        name = "fake"
        vers = "fake"
        mock_oslogging._loggers = {}

        returned_logger = log.getLogger(name, vers)

        self.assertIn(name, mock_oslogging._loggers)
        mock_rally_context_adapter.assert_called_once_with(
            mock_log.getLogger(name),
            {"project": "rally", "version": vers})
        self.assertEqual(mock_oslogging._loggers[name], returned_logger)


class LogRallyContaxtAdapter(test.TestCase):

    @mock.patch("rally.common.logging.log")
    @mock.patch("rally.common.logging.oslogging.KeywordArgumentAdapter")
    def test_debug(self, mock_keyword_argument_adapter, mock_log):

        mock_log.RDEBUG = 123
        fake_msg = "fake message"
        radapter = log.RallyContextAdapter(mock.MagicMock(), "fakep")
        radapter.log = mock.MagicMock()

        radapter.debug(fake_msg)

        radapter.log.assert_called_once_with(mock_log.RDEBUG,
                                             fake_msg)


class ExceptionLoggerTestCase(test.TestCase):

    @mock.patch("rally.common.logging.is_debug")
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


class LogCatcherTestCase(test.TestCase):
    # FIXME(pboldin): These are really functional tests and should be moved
    #                 there when the infrastructure is ready
    def test_logcatcher(self):
        LOG = log.getLogger("testlogger")
        LOG.logger.setLevel(log.INFO)

        with log.LogCatcher(LOG) as catcher:
            LOG.warning("Warning")
            LOG.info("Info")
            LOG.debug("Debug")

        catcher.assertInLogs("Warning")
        self.assertRaises(AssertionError, catcher.assertInLogs, "Error")

        self.assertEqual(["Warning", "Info"], catcher.fetchLogs())
        self.assertEqual(2, len(catcher.fetchLogRecords()))


class CatcherHandlerTestCase(test.TestCase):
    @mock.patch("logging.handlers.BufferingHandler.__init__")
    def test_init(self, mock_buffering_handler___init__):
        catcher_handler = log.CatcherHandler()
        mock_buffering_handler___init__.assert_called_once_with(
            catcher_handler, 0)

    def test_shouldFlush(self):
        catcher_handler = log.CatcherHandler()
        self.assertFalse(catcher_handler.shouldFlush())

    def test_emit(self):
        catcher_handler = log.CatcherHandler()
        catcher_handler.buffer = mock.Mock()

        catcher_handler.emit("foobar")

        catcher_handler.buffer.append.assert_called_once_with("foobar")


class LogCatcherUnitTestCase(test.TestCase):
    def setUp(self):
        super(LogCatcherUnitTestCase, self).setUp()
        patcher = mock.patch("rally.common.logging.CatcherHandler")
        self.catcher_handler = patcher.start()
        self.catcher_handler.return_value.buffer = [
            mock.Mock(msg="foo"), mock.Mock(msg="bar")]
        self.addCleanup(patcher.stop)

        self.logger = mock.Mock()

    def test_init(self):
        catcher = log.LogCatcher(self.logger)

        self.assertEqual(self.logger.logger, catcher.logger)
        self.assertEqual(self.catcher_handler.return_value, catcher.handler)
        self.catcher_handler.assert_called_once_with()

    def test_enter(self):
        catcher = log.LogCatcher(self.logger)

        self.assertEqual(catcher, catcher.__enter__())
        self.logger.logger.addHandler.assert_called_once_with(
            self.catcher_handler.return_value)

    def test_exit(self):
        catcher = log.LogCatcher(self.logger)

        catcher.__exit__(None, None, None)
        self.logger.logger.removeHandler.assert_called_once_with(
            self.catcher_handler.return_value)

    def test_assertInLogs(self):
        catcher = log.LogCatcher(self.logger)

        self.assertEqual(["foo"], catcher.assertInLogs("foo"))
        self.assertEqual(["bar"], catcher.assertInLogs("bar"))
        self.assertRaises(AssertionError, catcher.assertInLogs, "foobar")

    def test_assertInLogs_contains(self):
        catcher = log.LogCatcher(self.logger)

        record_mock = mock.MagicMock()
        self.catcher_handler.return_value.buffer = [record_mock]
        record_mock.msg.__contains__.return_value = True
        self.assertEqual([record_mock.msg], catcher.assertInLogs("foo"))

        record_mock.msg.__contains__.assert_called_once_with("foo")

    def test_fetchLogRecords(self):
        catcher = log.LogCatcher(self.logger)

        self.assertEqual(self.catcher_handler.return_value.buffer,
                         catcher.fetchLogRecords())

    def test_fetchLogs(self):
        catcher = log.LogCatcher(self.logger)

        self.assertEqual(
            [r.msg for r in self.catcher_handler.return_value.buffer],
            catcher.fetchLogs())
