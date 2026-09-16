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

import enum
import importlib.metadata
import inspect
import typing as t
from unittest import mock

import typing_extensions as te

from rally import plugins
from rally.common import validation
from rally.common.plugin import plugin
from rally.task import scenario
from rally.task import types
from rally.utils import rstutils
from tests.unit import test


REPOSITORIES = [
    rstutils.SourceRepository(
        package="tests",
        url="https://github.com/openstack/rally",
        ref="5.1.0",
    )
]


class Flavor(enum.Enum):
    TINY = "m1.tiny"
    SMALL = "m1.small"


class BootSpec(te.TypedDict, closed=True):
    name: str
    count: te.NotRequired[int]
    admin_pass: te.NotRequired[te.Never]


def create_server(name: str, *, flavor: str = "m1.tiny", **kwargs):
    pass


@plugin.configure(name="rstutils_image")
class ImageType(types.ResourceType):
    def pre_process(self, *, resource_spec: str | dict[str, str], config,
                    output_type):
        return resource_spec


@validation.add("required_platform", platform="rstutils", admin=True,
                users=True)
@validation.add("required_platform", platform="rstutils_admin", admin=True)
@validation.add("required_platform", platform="rstutils_users", users=True)
@scenario.configure(name="RSTUtils.boot", platform="rstutils")
class BootScenario(scenario.Scenario):
    def run(
        self,
        image: t.Annotated[str, types.Convert("rstutils_image")],
        name: t.Annotated[str, scenario.Field(pattern="^[a-z]+$")],
        count: t.Annotated[int, scenario.Field(ge=1, le=10)] = 1,
        ratio: t.Annotated[float, scenario.Field(gt=0, lt=1)] = 0.5,
        wait: bool = True,
        mode: t.Literal["fast", "slow", None] = "fast",
        flavor: Flavor = Flavor.TINY,
        size: str | int | None = None,
        tags: list[str] | None = None,
        spec: BootSpec | None = None,
        server_kwargs: t.Annotated[
            dict[str, t.Any], scenario.ArgsOf(create_server)
        ] | None = None,
        **kwargs,
    ):
        """Boot a server.

        Boots a server and waits for it to become active.

        :param image: image to boot the server from
        :param name: name of the server
        :param count: how many servers to boot
        :param ratio: share of servers to wait for
        :param wait: whether to wait for servers
        :param mode: how to boot servers
        :param flavor: flavor of servers
        :param size: size of the disk, in gigabytes or as a string like "10G"
        :param tags: tags to set
        :param spec: full specification of the server
        :param server_kwargs: extra arguments of the server
        :param kwargs: arguments for the boot request
        """


BOOT_SCENARIO_RST = inspect.cleandoc('''
    RSTUtils.boot
    """""""""""""

    Boot a server.

    Boots a server and waits for it to become active.

    **Platform**: rstutils

    **Parameters**:

    .. _rstutils-boot-image:

    * *image (string/dictionary, required)* [ref__]

      Image to boot the server from

    __ #rstutils-boot-image

    .. _rstutils-boot-name:

    * *name (string, required)* [ref__]

      Name of the server

      Should follow next pattern: ^[a-z]+$.

    __ #rstutils-boot-name

    .. _rstutils-boot-count:

    * *count (integer)* [ref__]

      How many servers to boot

      Min value: 1.

      Max value: 10.

      Defaults to ``1``.

    __ #rstutils-boot-count

    .. _rstutils-boot-ratio:

    * *ratio (number)* [ref__]

      Share of servers to wait for

      Min value: 0 (exclusive).

      Max value: 1 (exclusive).

      Defaults to ``0.5``.

    __ #rstutils-boot-ratio

    .. _rstutils-boot-wait:

    * *wait (boolean)* [ref__]

      Whether to wait for servers

      Defaults to ``true``.

    __ #rstutils-boot-wait

    .. _rstutils-boot-mode:

    * *mode* [ref__]

      How to boot servers

      Set of expected values: ``"fast"``, ``"slow"``, ``null``.

      Defaults to ``"fast"``.

    __ #rstutils-boot-mode

    .. _rstutils-boot-flavor:

    * *flavor* [ref__]

      Flavor of servers

      Set of expected values: ``"m1.tiny"``, ``"m1.small"``.

      Defaults to ``"m1.tiny"``.

    __ #rstutils-boot-flavor

    .. _rstutils-boot-size:

    * *size (string/integer/null)* [ref__]

      Size of the disk, in gigabytes or as a string like "10G"

    __ #rstutils-boot-size

    .. _rstutils-boot-tags:

    * *tags (list/null)* [ref__]

      Tags to set

      Elements of the list should follow format(s) described below:

      - Type: string.

    __ #rstutils-boot-tags

    .. _rstutils-boot-spec:

    * *spec (dictionary/null)* [ref__]

      Full specification of the server

      - *name (string, required)*

      - *count (integer)*

      **Restricted parameters**: admin_pass

    __ #rstutils-boot-spec

    .. _rstutils-boot-server-kwargs:

    * *server_kwargs (dictionary/null)* [ref__]

      Extra arguments of the server

      - *name (string, required)*

      - *flavor (string)*

        Defaults to ``"m1.tiny"``.

      **Additional parameters**: accepted

    __ #rstutils-boot-server-kwargs

    **Additional parameters**: arguments for the boot request

    **Requires platform(s)**:

    * rstutils_users with regular users (temporary users can be created via the 'users' context if admin user is specified for the platform).
    * rstutils_admin with credentials for admin user.
    * rstutils with credentials for admin user and regular users (temporary users can be created via the 'users' context if admin user is specified for the platform).

    **Module**:
    `tests.unit.utils.test_rstutils`__

    __ https://github.com/openstack/rally/blob/5.1.0/tests/unit/utils/test_rstutils.py
''')  # noqa: E501


@plugin.configure(name="rstutils_one_of")
class OneOfPlugin(plugin.Plugin):
    """Trigger by one of the units.

    :returns: nothing
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "oneOf": [
            {
                "description": "Trigger at iterations.",
                "properties": {
                    "name": {"type": "string", "description": "the name"},
                    "unit": {
                        "enum": ["iteration"],
                        "description": "unit of the trigger\n",
                    },
                    "at": {
                        "type": "array",
                        "items": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "\nthe iteration\n\nstarts at 1\n",
                        },
                    },
                },
                "required": ["unit", "at"],
            },
            {
                "properties": {
                    "name": {"type": "string", "description": "the name"},
                    "unit": {"enum": ["time"]},
                    "step": {"type": "number", "maximum": 60},
                    "old": False,
                },
                "required": ["unit"],
            },
        ],
        "additionalProperties": False,
    }


ONE_OF_RST = inspect.cleandoc('''
    rstutils_one_of [Hook Trigger]
    """"""""""""""""""""""""""""""

    Trigger by one of the units.

    **Platform**: default

    **Parameters**:

    .. _hook-trigger-rstutils-one-of-name:

    * *name (string)* [ref__]

      The name

    __ #hook-trigger-rstutils-one-of-name

    .. note:: One of the following groups of parameters should be provided.

    **Option 1 of parameters**:

    Trigger at iterations.

    .. _hook-trigger-rstutils-one-of-option-1-unit:

    * *unit (required)* [ref__]

      Unit of the trigger

      Expected value: ``"iteration"``.

    __ #hook-trigger-rstutils-one-of-option-1-unit

    .. _hook-trigger-rstutils-one-of-option-1-at:

    * *at (list, required)* [ref__]

      Elements of the list should follow format(s) described below:

      - Type: integer.

        The iteration

        starts at 1

        Min value: 1.

    __ #hook-trigger-rstutils-one-of-option-1-at

    **Option 2 of parameters**:

    .. _hook-trigger-rstutils-one-of-option-2-unit:

    * *unit (required)* [ref__]

      Expected value: ``"time"``.

    __ #hook-trigger-rstutils-one-of-option-2-unit

    .. _hook-trigger-rstutils-one-of-option-2-step:

    * *step (number)* [ref__]

      Max value: 60.

    __ #hook-trigger-rstutils-one-of-option-2-step

    **Restricted parameters**: old

    **Returns**:
    nothing

    **Module**:
    `tests.unit.utils.test_rstutils`__

    __ https://github.com/openstack/rally/blob/5.1.0/tests/unit/utils/test_rstutils.py
''')  # noqa: E501


@plugin.configure(name="rstutils_patterns")
class PatternsPlugin(plugin.Plugin):
    """Map of the services."""

    CONFIG_SCHEMA = {
        "type": "object",
        "patternProperties": {
            "^[a-z]+$": {"type": "string", "description": "the version"},
            ".*": {"type": "integer"},
        },
        "additionalProperties": {"description": "legacy services"},
    }


PATTERNS_RST = inspect.cleandoc('''
    rstutils_patterns
    """""""""""""""""

    Map of the services.

    **Platform**: default

    **Parameters**:

    *Dictionary is expected. Keys should follow pattern(s) described below.*

    .. _rstutils-patterns-pattern-1:

    * ``^[a-z]+$`` *(string)* [ref__]

      The version

    __ #rstutils-patterns-pattern-1

    .. _rstutils-patterns-pattern-2:

    * ``.*`` *(string)* [ref__]

    __ #rstutils-patterns-pattern-2

    **Additional parameters**: legacy services

    **Module**:
    `tests.unit.utils.test_rstutils`__

    __ https://github.com/openstack/rally/blob/5.1.0/tests/unit/utils/test_rstutils.py
''')  # noqa: E501


@plugin.configure(name="rstutils_number")
class NumberPlugin(plugin.Plugin):
    """Maximum duration."""

    CONFIG_SCHEMA = {
        "type": ["number", "null"],
        "minimum": 0.0,
        "exclusiveMinimum": True,
        "description": "seconds per iteration",
    }


NUMBER_RST = inspect.cleandoc('''
    rstutils_number
    """""""""""""""

    Maximum duration.

    **Platform**: default

    **Input value**: *number/null*

    Seconds per iteration

    Min value: 0.0 (exclusive).

    **Module**:
    `tests.unit.utils.test_rstutils`__

    __ https://github.com/openstack/rally/blob/5.1.0/tests/unit/utils/test_rstutils.py
''')  # noqa: E501


@plugin.configure(name="rstutils_null")
class NullPlugin(plugin.Plugin):
    """Takes no configuration."""

    CONFIG_SCHEMA = {"type": "null"}


NULL_RST = inspect.cleandoc('''
    rstutils_null
    """""""""""""

    Takes no configuration.

    **Platform**: default

    **Input value**: *null*

    **Module**:
    `tests.unit.utils.test_rstutils`__

    __ https://github.com/openstack/rally/blob/5.1.0/tests/unit/utils/test_rstutils.py
''')  # noqa: E501


@plugin.configure(name="rstutils_nested")
class NestedPlugin(plugin.Plugin):
    """Boot a server."""

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "image_name": {"type": "string"},
            "image_url": {"type": "string"},
            "flavor": {"type": "string"},
            "rps": {
                "description": "requests per second",
                "anyOf": [
                    {"type": "number", "description": "a constant rate"},
                    {
                        "type": "object",
                        "description": "an increasing rate",
                        "properties": {
                            "start": {"$ref": "#/definitions/positive"},
                            "step": {"$ref": "#/definitions/positive"},
                        },
                        "required": ["start"],
                        "additionalProperties": False,
                    },
                ],
            },
            "nics": {
                "type": "array",
                "items": {
                    "oneOf": [
                        {"type": "string", "description": "a network ID"},
                        {
                            "type": "object",
                            "properties": {
                                "net-id": {"type": "string"},
                                "mtu": {
                                    "anyOf": [
                                        {"type": "integer"},
                                        {"type": "string"},
                                    ]
                                },
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "additionalProperties": False,
                        },
                    ]
                },
            },
            "user": {"$ref": "#/definitions/user"},
            "services": {
                "type": "object",
                "patternProperties": {
                    "^[a-z]+$": {"type": "string", "description": "a version"},
                },
                "additionalProperties": {"description": "legacy services"},
            },
            "command": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {"script": {"type": "string"}},
                    },
                    {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                    },
                ]
            },
        },
        "oneOf": [
            {"description": "by name", "required": ["flavor", "image_name"]},
            {"description": "by URL", "required": ["flavor", "image_url"]},
        ],
        "additionalProperties": False,
        "definitions": {
            "positive": {"type": "number", "minimum": 1},
            "user": {
                "type": "object",
                "description": "the owner",
                "properties": {"username": {"type": "string"}},
                "anyOf": [
                    {
                        "description": "Keystone V3",
                        "properties": {"project": {"type": "string"}},
                        "required": ["project"],
                    },
                    {
                        "description": "Keystone V2",
                        "properties": {"tenant": {"type": "string"}},
                        "required": ["tenant"],
                    },
                ],
                "additionalProperties": False,
            },
        },
    }


NESTED_RST = inspect.cleandoc('''
    rstutils_nested
    """""""""""""""

    Boot a server.

    **Platform**: default

    **Parameters**:

    .. _rstutils-nested-image-name:

    * *image_name (string)* [ref__]

    __ #rstutils-nested-image-name

    .. _rstutils-nested-image-url:

    * *image_url (string)* [ref__]

    __ #rstutils-nested-image-url

    .. _rstutils-nested-flavor:

    * *flavor (string, required)* [ref__]

    __ #rstutils-nested-flavor

    .. _rstutils-nested-rps:

    * *rps (number/dictionary)* [ref__]

      Requests per second

      One of:

      - *number*

        A constant rate

      - *dictionary*

        An increasing rate

        - *start (number, required)*

          Min value: 1.

        - *step (number)*

          Min value: 1.

    __ #rstutils-nested-rps

    .. _rstutils-nested-nics:

    * *nics (list)* [ref__]

      Elements of the list should follow format(s) described below:

      One of:

      - *string*

        A network ID

      - *dictionary*

        - *net-id (string)*

        - *mtu (integer/string)*

        - *tags (list)*

          Format:

          .. code-block:: json

              {
                  "type": "array",
                  "items": {
                      "type": "string"
                  }
              }

    __ #rstutils-nested-nics

    .. _rstutils-nested-user:

    * *user (dictionary)* [ref__]

      The owner

      - *username (string)*

      One of the following groups of parameters should be provided:

      - *Option 1*

        Keystone V3

        - *project (string, required)*

      - *Option 2*

        Keystone V2

        - *tenant (string, required)*

    __ #rstutils-nested-user

    .. _rstutils-nested-services:

    * *services (dictionary)* [ref__]

      Keys should follow pattern(s) described below:

      - ``^[a-z]+$`` *(string)*

        A version

      **Additional parameters**: legacy services

    __ #rstutils-nested-services

    .. _rstutils-nested-command:

    * *command (dictionary)* [ref__]

      One of:

      - *Option 1*

        - *script (string)*

      - *Option 2*

        - *path (string)*

    __ #rstutils-nested-command

    .. note:: One of the following groups of parameters should be provided:

       - ``image_name``

         By name

       - ``image_url``

         By URL

    **Module**:
    `tests.unit.utils.test_rstutils`__

    __ https://github.com/openstack/rally/blob/5.1.0/tests/unit/utils/test_rstutils.py
''')  # noqa: E501


@plugin.configure(name="rstutils_linked")
class LinkedPlugin(plugin.Plugin):
    """Linked."""


@plugin.configure(name="rstutils_unknown")
class UnknownPlugin(plugin.Plugin):
    """Unknown."""


class RSTUtilsTestCase(test.TestCase):

    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def test_make_plugin_section(self):
        with self.subTest("schema for complex Scenario plugin"):
            self.assertEqual(
                f"{BOOT_SCENARIO_RST}\n",
                rstutils.make_plugin_section(
                    BootScenario, repositories=REPOSITORIES
                ),
            )

        with self.subTest("schema with oneOf"):
            self.assertEqual(
                f"{ONE_OF_RST}\n",
                rstutils.make_plugin_section(
                    OneOfPlugin, base_name="Hook Trigger",
                    repositories=REPOSITORIES
                ),
            )

        with self.subTest("schema with patternProperties"):
            self.assertEqual(
                f"{PATTERNS_RST}\n",
                rstutils.make_plugin_section(
                    PatternsPlugin, repositories=REPOSITORIES
                ),
            )

        with self.subTest("single value schema"):
            self.assertEqual(
                f"{NUMBER_RST}\n",
                rstutils.make_plugin_section(
                    NumberPlugin, repositories=REPOSITORIES
                ),
            )

        with self.subTest("null schema"):
            self.assertEqual(
                f"{NULL_RST}\n",
                rstutils.make_plugin_section(
                    NullPlugin, repositories=REPOSITORIES
                ),
            )

        with self.subTest("schema with nested values and references"):
            self.assertEqual(
                f"{NESTED_RST}\n",
                rstutils.make_plugin_section(
                    NestedPlugin, repositories=REPOSITORIES
                ),
            )

    def test_make_plugin_section_of_rally_plugins_is_tidy(self):
        plugins.load()
        rally_plugins = [
            p for p in plugin.Plugin.get_all(allow_hidden=True)
            if p.__module__.startswith("rally.")
        ]
        self.assertNotEqual([], rally_plugins)

        for plugin_cls in rally_plugins:
            name = f"{plugin_cls.get_name()}@{plugin_cls.get_platform()}"
            with self.subTest(plugin=name):
                section = rstutils.make_plugin_section(plugin_cls)
                lines = section.split("\n")

                self.assertEqual(
                    [],
                    [i for i, line in enumerate(lines, 1)
                     if line != line.rstrip()],
                    f"Lines with trailing whitespace:\n{section}",
                )
                self.assertNotIn("\n\n\n", section)
                self.assertTrue(section.endswith("\n"))
                self.assertFalse(section.endswith("\n\n"))

    def test_make_plugin_section_links_to_default_repositories(self):
        for module, version, url in (
            ("rally.plugins.task.fake", "5.1.0",
             "https://github.com/openstack/rally/blob/5.1.0/"
             "rally/plugins/task/fake.py"),
            ("rally.plugins.task.fake", "5.1.1.dev3",
             "https://github.com/openstack/rally/blob/master/"
             "rally/plugins/task/fake.py"),
            ("rally_openstack.task.fake", "4.1.0",
             "https://github.com/openstack/rally-openstack/blob/4.1.0/"
             "rally_openstack/task/fake.py"),
            ("rally_openstack.task.fake", "4.2.0.0rc1",
             "https://github.com/openstack/rally-openstack/blob/master/"
             "rally_openstack/task/fake.py"),
        ):
            with self.subTest(module=module, version=version):
                # the installed versions are looked up once per process
                rstutils._default_repositories.cache_clear()
                self.addCleanup(rstutils._default_repositories.cache_clear)
                with mock.patch.object(LinkedPlugin, "__module__", module):
                    with mock.patch.object(importlib.metadata, "version",
                                           return_value=version):
                        section = rstutils.make_plugin_section(LinkedPlugin)

                self.assertEqual(
                    inspect.cleandoc(f'''
                        rstutils_linked
                        """""""""""""""

                        Linked.

                        **Platform**: default

                        **Module**:
                        `{module}`__

                        __ {url}
                    ''') + "\n",
                    section,
                )

        with self.subTest("versions are looked up once"):
            rstutils._default_repositories.cache_clear()
            with mock.patch.object(importlib.metadata, "version",
                                   return_value="5.1.0") as m_version:
                with mock.patch.object(LinkedPlugin, "__module__",
                                       "rally.plugins.task.fake"):
                    rstutils.make_plugin_section(LinkedPlugin)
                    rstutils.make_plugin_section(LinkedPlugin)

            # one lookup for rally and one for rally-openstack
            self.assertEqual(2, m_version.call_count)

    def test_make_plugin_section_of_unknown_module(self):
        e = self.assertRaises(ValueError, rstutils.make_plugin_section,
                              UnknownPlugin)
        self.assertEqual(
            "Plugin 'rstutils_unknown' is defined in module "
            "'tests.unit.utils.test_rstutils' that does not belong to any "
            "known repository.",
            str(e),
        )

    def test_source_repository_from_distribution(self):
        url = "https://github.com/openstack/rally-openstack"

        for version, ref in (
            ("4.1.0", "4.1.0"),
            ("4.1.1.dev2", "master"),
            ("4.2.0rc1", "master"),
            ("4.1.0.post1", "master"),
            ("4.1.0+local", "master"),
            ("not a version", "master"),
        ):
            with self.subTest(version=version):
                with mock.patch.object(importlib.metadata, "version",
                                       return_value=version) as m_version:
                    repository = rstutils.SourceRepository.from_distribution(
                        "rally_openstack", url,
                        distribution="rally-openstack",
                    )

                m_version.assert_called_once_with("rally-openstack")
                self.assertEqual(
                    rstutils.SourceRepository(
                        package="rally_openstack", url=url, ref=ref
                    ),
                    repository,
                )

        with mock.patch.object(
            importlib.metadata, "version",
            side_effect=importlib.metadata.PackageNotFoundError
        ):
            repository = rstutils.SourceRepository.from_distribution(
                "rally_openstack", url, distribution="rally-openstack",
            )
        self.assertEqual("master", repository.ref)
