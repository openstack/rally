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

import collections
import json

import yaml
from yaml import constructor
from yaml import loader
from yaml import nodes
from yaml import parser
from yaml import resolver

ParserError = parser.ParserError


# NOTE(andreykurilin): Jinja2 uses __repr__ methods of objects while rendering
#   templates. Such behaviour converts OrderedDict to the string like
#        "OrderedDict([('foo', 'xxx'), ('bar', 'yyy')])"
#   which breaks json/yaml load.
#   In 99% of cases, we are rendering templates based on the dicts obtained
#   after yaml.safe_load which uses collections.OrderedDict , so writing here
#   the workaround with overridden __repr__ method looks like the best choice.
class OrderedDict(collections.OrderedDict):
    """collections.OrderedDict with __repr__ like in the regular dict."""
    def __repr__(self):
        return json.dumps(self, sort_keys=False)


def _construct_mapping(loader, node, deep=False):
    keys = []
    if isinstance(node, nodes.MappingNode):
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in keys:
                raise constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "the key (%s) is redefined" % key,
                    key_node.start_mark)
            keys.append(key)
    return OrderedDict(loader.construct_pairs(node))


class _SafeLoader(loader.SafeLoader):
    pass


_SafeLoader.add_constructor(resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                            _construct_mapping)


def safe_load(stream):
    """Load stream to create python object

    :param stream: json/yaml stream.
    :returns: dict object
    """
    return yaml.load(stream, _SafeLoader)
