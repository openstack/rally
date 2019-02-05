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

from docutils import frontend
from docutils.parsers import rst
from docutils import utils
import sys

import mock


@mock.patch.object(sys, "stderr")
def parse_rst(text, mock_stderr):
    parser = rst.Parser()
    settings = frontend.OptionParser(
        components=(rst.Parser,)).get_default_values()
    document = utils.new_document(text, settings)
    parser.parse(text, document)
    return document.children
