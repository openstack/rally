import copy

import mock

from rally import exceptions
from rally.plugins.common.exporters.monasca import exporter
from tests.unit import test
import imp
import os


PATH = "rally.plugins.common.exporters.monasca.exporter"
DIR=os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(DIR, "config.py")

config_single_dimension= """
dimensions = {
    'rally': {"dimension1": "path.in.report"}
}
"""

config_single_override = """
dimensions = {
    'rally': {"dimension1": "path.in.report"},
    'rally.action.Nova.Bootserver': {"dimension1": "override1"},
    'rally.action.Nova.Bootserver.success': {"dimension1": "should.not.override"}
}
"""

config_dual_override = """
dimensions = {
    'rally': {"dimension1": "path.in.report"},
    'rally.action.Nova.Bootserver': {"dimension1": "override1"},
    'rally.action.Nova.Bootserver.duration': {"dimension1": "override2"},
    'rally.action.Nova.Bootserver.success': {"dimension1": "should.not.override"}
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
        result = exporter._load_config(CONFIG_PATH, "rally.action.Nova.Bootserver.duration")
        expected = {'dimension1': 'path.in.report'}
        self.assertEquals(expected, result)

    @mock.patch("%s._load_module" % PATH)
    def test_config_file_overide(self, mock_load_module):
        mock_load_module.side_effect = [mock_module(config_single_override)]
        result = exporter._load_config(CONFIG_PATH, "rally.action.Nova.Bootserver.duration")
        expected = {'dimension1': 'override1'}
        self.assertEquals(expected, result)

    @mock.patch("%s._load_module" % PATH)
    def test_config_file_overide2(self, mock_load_module):
        mock_load_module.side_effect = [mock_module(config_dual_override)]
        result = exporter._load_config(CONFIG_PATH, "rally.action.Nova.Bootserver.duration")
        expected = {'dimension1': 'override2'}
        self.assertEquals(expected, result)




