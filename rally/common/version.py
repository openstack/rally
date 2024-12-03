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


from importlib.metadata import version as _version

from rally.common.plugin import discover as rally_discover

RALLY_VENDOR = "OpenStack Foundation"
RALLY_PRODUCT = "OpenStack Rally"

try:
    # Try to get version from installed package metadata
    __version__ = _version("rally")
except Exception:
    # Fallback to setuptools_scm for development installs
    try:
        from setuptools_scm import get_version

        __version__ = get_version()
    except Exception:
        # Final fallback - this should rarely happen
        __version__ = "0.0.0"


__version_tuple__ = tuple(
    int(p) if p.isdigit() else p
    for p in __version__.replace("-", ".").split(".")
)


def database_revision():
    from rally.common.db import schema

    return schema.schema_revision(detailed=True)


def plugins_versions():
    """Show packages version"""

    return dict(
        (ep.dist.name, ep.dist.version)
        for ep in rally_discover.iter_entry_points()
    )


# backward compatibility
class version_info:

    @classmethod
    def semantic_version(cls):
        return cls

    @classmethod
    def version_tuple(cls):
        return __version_tuple__


def version_string():
    return __version__
