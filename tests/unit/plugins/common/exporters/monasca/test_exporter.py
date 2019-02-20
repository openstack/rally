import copy

import mock

from rally import exceptions
from rally.plugins.common.exporters.monasca import exporter
from tests.unit import test
import imp
import os


PATH = "rally.plugins.common.exporters.monasca.exporter"
DUMMY_CONFIG_PATH = "/tmp"

config_single_dimension= """
dimensions = {
    'rally': {"dimension1": {"path_in_report": "path.in.report"}}
}
"""

config_single_override = """
dimensions = {
    'rally': {"dimension1": {"path_in_report": "path.in.report"}},
    'rally.action.Nova.Bootserver': {"dimension1": {"path_in_report": "override1"}},
    'rally.action.Nova.Bootserver.success': {"dimension1": {"path_in_report": "should.not.override"}}
}
"""

config_dual_override = """
dimensions = {
    'rally': {"dimension1": {"path_in_report": "path.in.report"}},
    'rally.action.Nova.Bootserver': {"dimension1": {"path_in_report": "override1"}},
    'rally.action.Nova.Bootserver.duration': {"dimension1": {"path_in_report": "override2"}},
    'rally.action.Nova.Bootserver.success': {"dimension1": {"path_in_report": "should.not.override"}}
}
"""

config_proto = """
dimensions = {
    'rally': {
        "task_uuid": {"path_in_report": "task.uuid"},
        "tags": {"path_in_report": "task.tags"},
        # we want the following for both actions and workloads
        "args_hash": {"path_in_report": "workload.args_hash"},
        "runner_hash": {"path_in_report": "workload.runner_hash"},
        "contexts_hash": {"path_in_report": "workload.contexts_hash"},
        "subtask_uuid": {"path_in_report": "workload.subtask_uuid"}   ,     
    },
    'rally.workload': {
        "uuid": {"path_in_report": "workload.uuid"},
    },
    'rally.action': {
        "uuid": {"path_in_report": "workload.uuid"},
    }
}

"""

def mock_module(code):
    module = imp.new_module('mymodule')
    exec(code, module.__dict__)
    return module

class MonascaClientTestCase(test.TestCase):

    @mock.patch("%s._load_module" % PATH)
    def test_config_file(self, mock_load_module):
        mock_load_module.side_effect = [mock_module(config_single_dimension)]
        result = exporter._load_config(DUMMY_CONFIG_PATH, "rally.action.Nova.Bootserver.duration")
        expected = {'dimension1': {'path_in_report': 'path.in.report'}}
        self.assertEquals(expected, result)

    @mock.patch("%s._load_module" % PATH)
    def test_config_file_overide(self, mock_load_module):
        mock_load_module.side_effect = [mock_module(config_single_override)]
        result = exporter._load_config(DUMMY_CONFIG_PATH, "rally.action.Nova.Bootserver.duration")
        expected = {'dimension1': {'path_in_report': 'override1'}}
        self.assertEquals(expected, result)

    @mock.patch("%s._load_module" % PATH)
    def test_config_file_overide2(self, mock_load_module):
        mock_load_module.side_effect = [mock_module(config_dual_override)]
        result = exporter._load_config(DUMMY_CONFIG_PATH, "rally.action.Nova.Bootserver.duration")
        expected = {'dimension1': {'path_in_report':'override2'}}
        self.assertEquals(expected, result)




