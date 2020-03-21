#
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

import logging   # noqa
from unittest import mock

from rally.common import logging as rally_logging
from tests.unit import test


class SetUpLogTestCase(test.TestCase):

    @mock.patch("rally.common.logging.CONF")
    @mock.patch("rally.common.logging.handlers")
    @mock.patch("rally.common.logging.oslogging")
    def test_setup(self, mock_oslogging, mock_handlers, mock_conf):

        proj = "fakep"
        version = "fakev"
        mock_handlers.ColorHandler.LEVEL_COLORS = {
            logging.DEBUG: "debug_color"}
        mock_conf.rally_debug = True

        rally_logging.setup(proj, version)

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

        returned_logger = rally_logging.getLogger(name, vers)

        self.assertIn(name, mock_oslogging._loggers)
        mock_rally_context_adapter.assert_called_once_with(
            mock_log.getLogger(name),
            {"project": "rally", "version": vers})
        self.assertEqual(mock_oslogging._loggers[name], returned_logger)


class RallyContaxtAdapterTestCase(test.TestCase):

    @mock.patch("rally.common.logging.log")
    @mock.patch("rally.common.logging.oslogging.KeywordArgumentAdapter")
    def test_debug(self, mock_keyword_argument_adapter, mock_log):

        mock_log.RDEBUG = 123
        fake_msg = "fake message"
        radapter = rally_logging.RallyContextAdapter(mock.MagicMock(), "fakep")
        radapter.log = mock.MagicMock()

        radapter.debug(fake_msg)

        radapter.log.assert_called_once_with(mock_log.RDEBUG,
                                             fake_msg)

    def test__find_caller(self):
        radapter = rally_logging.RallyContextAdapter(mock.MagicMock(), "fakep")

        self.caller = None

        def logging_method():
            self.caller = radapter._find_the_caller()

        def foo():
            logging_method()

        foo()
        # the number of the line which calls logging_method
        lineno = 91
        self.assertEqual((__file__, lineno, "logging_method()"), self.caller)

    @mock.patch("rally.common.logging.getLogger")
    def test__check_args(self, mock_get_logger):
        radapter = rally_logging.RallyContextAdapter(mock.MagicMock(), "fakep")

        def foo(*args):
            radapter._check_args("", *args)

        foo()

        self.assertFalse(mock_get_logger.called)

        foo(1)

        # the number of the line which calls foo
        lineno = 109
        mock_get_logger.assert_called_once_with("%s:%s" % (__file__, lineno))
        logger = mock_get_logger.return_value
        self.assertEqual(1, logger.warning.call_count)
        args = logger.warning.call_args_list[0]
        self.assertTrue(args[0][0].startswith("[foo(1)] Do not use"))

    @mock.patch("rally.common.logging.getLogger")
    def test_exception(self, mock_get_logger):
        radapter = rally_logging.RallyContextAdapter(mock.MagicMock(), {})
        radapter.log = mock.MagicMock()

        radapter.exception("foo")

        self.assertFalse(mock_get_logger.called)

        radapter.exception(Exception("!2!"))

        # the number of the line which calls foo
        lineno = 128
        mock_get_logger.assert_called_once_with("%s:%s" % (__file__, lineno))

        logger = mock_get_logger.return_value
        self.assertEqual(1, logger.warning.call_count)
        args = logger.warning.call_args_list[0]
        self.assertTrue(args[0][0].startswith("[radapter.exception(Exception("
                                              "\"!2!\"))] Do not transmit"))

    @mock.patch("rally.common.logging.getLogger")
    def test_error(self, mock_get_logger):
        radapter = rally_logging.RallyContextAdapter(mock.MagicMock(), {})
        radapter.log = mock.MagicMock()

        radapter.error("foo", "bar")

        # the number of the line which calls foo
        lineno = 145
        mock_get_logger.assert_called_once_with("%s:%s" % (__file__, lineno))

        logger = mock_get_logger.return_value
        self.assertEqual(1, logger.warning.call_count)
        args = logger.warning.call_args_list[0]
        self.assertTrue(args[0][0].startswith("[radapter.error(\"foo\", "
                                              "\"bar\")] Do not use *args "))


class ExceptionLoggerTestCase(test.TestCase):

    @mock.patch("rally.common.logging.is_debug")
    def test_context(self, mock_is_debug):
        # Prepare
        mock_is_debug.return_value = True

        logger = mock.MagicMock()
        exception = Exception()

        # Run
        with rally_logging.ExceptionLogger(logger, "foo") as e:
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
        LOG = rally_logging.getLogger("testlogger")
        LOG.logger.setLevel(rally_logging.INFO)

        with rally_logging.LogCatcher(LOG) as catcher:
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
        catcher_handler = rally_logging.CatcherHandler()
        mock_buffering_handler___init__.assert_called_once_with(
            catcher_handler, 0)

    def test_shouldFlush(self):
        catcher_handler = rally_logging.CatcherHandler()
        self.assertFalse(catcher_handler.shouldFlush())

    def test_emit(self):
        catcher_handler = rally_logging.CatcherHandler()
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
        catcher = rally_logging.LogCatcher(self.logger)

        self.assertEqual(self.logger.logger, catcher.logger)
        self.assertEqual(self.catcher_handler.return_value, catcher.handler)
        self.catcher_handler.assert_called_once_with()

    def test_enter(self):
        catcher = rally_logging.LogCatcher(self.logger)

        self.assertEqual(catcher, catcher.__enter__())
        self.logger.logger.addHandler.assert_called_once_with(
            self.catcher_handler.return_value)

    def test_exit(self):
        catcher = rally_logging.LogCatcher(self.logger)

        catcher.__exit__(None, None, None)
        self.logger.logger.removeHandler.assert_called_once_with(
            self.catcher_handler.return_value)

    def test_assertInLogs(self):
        catcher = rally_logging.LogCatcher(self.logger)

        self.assertEqual(["foo"], catcher.assertInLogs("foo"))
        self.assertEqual(["bar"], catcher.assertInLogs("bar"))
        self.assertRaises(AssertionError, catcher.assertInLogs, "foobar")

    def test_assertInLogs_contains(self):
        catcher = rally_logging.LogCatcher(self.logger)

        record_mock = mock.MagicMock()
        self.catcher_handler.return_value.buffer = [record_mock]
        record_mock.msg.__contains__.return_value = True
        self.assertEqual([record_mock.msg], catcher.assertInLogs("foo"))

        record_mock.msg.__contains__.assert_called_once_with("foo")

    def test_fetchLogRecords(self):
        catcher = rally_logging.LogCatcher(self.logger)

        self.assertEqual(self.catcher_handler.return_value.buffer,
                         catcher.fetchLogRecords())

    def test_fetchLogs(self):
        catcher = rally_logging.LogCatcher(self.logger)

        self.assertEqual(
            [r.msg for r in self.catcher_handler.return_value.buffer],
            catcher.fetchLogs())


class LogTestCase(test.TestCase):

    def test_log_task_wrapper(self):
        mock_log = mock.MagicMock()
        msg = "test %(a)s %(b)s"

        class TaskLog(object):

            def __init__(self):
                self.task = {"uuid": "some_uuid"}

            @rally_logging.log_task_wrapper(mock_log, msg, a=10, b=20)
            def some_method(self, x, y):
                return x + y

        t = TaskLog()
        self.assertEqual("some_method", t.some_method.__name__)
        self.assertEqual(4, t.some_method(2, 2))
        params = {"msg": msg % {"a": 10, "b": 20}, "uuid": t.task["uuid"]}
        expected = [
            mock.call("Task %(uuid)s | Starting:  %(msg)s" % params),
            mock.call("Task %(uuid)s | Completed: %(msg)s" % params)
        ]
        self.assertEqual(expected, mock_log.mock_calls)

    def test_log_deprecated(self):
        mock_log = mock.MagicMock()

        @rally_logging.log_deprecated("depr42", "1.1.1", mock_log)
        def some_method(x, y):
            return x + y

        self.assertEqual(4, some_method(2, 2))
        self.assertIn("some_method()", mock_log.call_args[0][0])
        self.assertIn("depr42", mock_log.call_args[0][0])
        self.assertIn("1.1.1", mock_log.call_args[0][0])

    def test_log_deprecated_args(self):
        mock_log = mock.MagicMock()

        @rally_logging.log_deprecated_args("ABC42", "0.0.1", ("z",),
                                           mock_log, once=True)
        def some_method(x, y, z):
            return x + y + z

        self.assertEqual(7, some_method(2, 2, z=3))
        self.assertIn("ABC42", mock_log.call_args[0][0])
        self.assertIn("`z' of `some_method()'", mock_log.call_args[0][0])
        self.assertIn("0.0.1", mock_log.call_args[0][0])

        mock_log.reset_mock()
        self.assertEqual(7, some_method(2, 2, z=3))
        self.assertFalse(mock_log.called)

        @rally_logging.log_deprecated_args("CBA42", "0.0.1", ("z",),
                                           mock_log, once=False)
        def some_method(x, y, z):
            return x + y + z

        self.assertEqual(7, some_method(2, 2, z=3))
        self.assertIn("CBA42", mock_log.call_args[0][0])

        mock_log.reset_mock()
        self.assertEqual(7, some_method(2, 2, z=3))
        self.assertIn("CBA42", mock_log.call_args[0][0])
