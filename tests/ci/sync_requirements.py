#!/usr/bin/env python
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

"""
Synchronizes, formats and prepares requirements to release(obtains and adds
maximum allowed version).
"""

import argparse
import logging
import re
import sys
import textwrap

import requests


LOG = logging.getLogger(__name__)
if not LOG.handlers:
    LOG.addHandler(logging.StreamHandler())
    LOG.setLevel(logging.INFO)


GLOBAL_REQUIREMENTS_LOCATIONS = (
    "https://raw.githubusercontent.com/openstack/requirements/master/",
    "http://git.openstack.org/cgit/openstack/requirements/plain/"
)
GLOBAL_REQUIREMENTS_FILENAME = "global-requirements.txt"
RALLY_REQUIREMENTS_FILES = (
    "requirements.txt",
    "test-requirements.txt"
)
DO_NOT_TOUCH_TAG = "[do-not-touch]"


class Comment(object):
    def __init__(self, s=None, finished=False):
        self._comments = []
        self.is_finished = finished
        if s:
            self.append(s)

    def finish_him(self):
        self.is_finished = True

    def append(self, s):
        self._comments.append(s[1:].strip())

    def __str__(self):
        return textwrap.fill("\n".join(self._comments), width=80,
                             initial_indent="# ", subsequent_indent="# ")


class Requirement(object):
    RE_NAME = re.compile(r"[a-zA-Z0-9-._]+")
    RE_CONST_VERSION = re.compile(r"==[a-zA-Z0-9.]+")
    RE_MIN_VERSION = re.compile(r">=?[a-zA-Z0-9.]+")
    RE_MAX_VERSION = re.compile(r"<=?[a-zA-Z0-9.]+")
    RE_NE_VERSIONS = re.compile(r"!=[a-zA-Z0-9.]+")
    # NOTE(andreykurilin): one license can have different labels. Let's use
    #   unified variant.
    LICENSE_MAP = {"MIT license": "MIT",
                   "MIT License": "MIT",
                   "BSD License": "BSD",
                   "Apache 2.0": "Apache License, Version 2.0"}

    def __init__(self, package_name, version):
        self.package_name = package_name
        self.version = version
        self._license = None
        self._pypy_info = None
        self.do_not_touch = False

    def sync_max_version_with_pypy(self):
        if isinstance(self.version, dict) and not self.do_not_touch:
            self.version["max"] = "<=%s" % self.pypy_info["info"]["version"]

    @property
    def pypy_info(self):
        if self._pypy_info is None:
            resp = requests.get("https://pypi.python.org/pypi/%s/json" %
                                self.package_name)
            if resp.status_code != 200:
                raise Exception(resp.text)
            self._pypy_info = resp.json()
        return self._pypy_info

    @property
    def license(self):
        if self._license is None:
            if self.pypy_info["info"]["license"]:
                self._license = self.pypy_info["info"]["license"]
            else:
                # try to parse classifiers
                prefix = "License :: OSI Approved :: "
                classifiers = [c[len(prefix):]
                               for c in self.pypy_info["info"]["classifiers"]
                               if c.startswith(prefix)]
                self._license = "/".join(classifiers)
            self._license = self.LICENSE_MAP.get(self._license, self._license)
            if self._license == "UNKNOWN":
                self._license = None
        return self._license

    @classmethod
    def parse_line(cls, line):
        match = cls.RE_NAME.match(line)
        if match:
            name = match.group()
            # remove name
            versions = line.replace(name, "")
            # remove comments
            versions = versions.split("#")[0]
            # remove python classifiers
            versions = versions.split(";")[0].strip()
            if not cls.RE_CONST_VERSION.match(versions):
                versions = versions.strip().split(",")
                min_version = None
                max_version = None
                ne_versions = []
                for version in versions:
                    if cls.RE_MIN_VERSION.match(version):
                        if min_version:
                            raise Exception("Found several min versions for "
                                            "%s package." % name)
                        min_version = version
                    elif cls.RE_MAX_VERSION.match(version):
                        if max_version:
                            raise Exception("Found several max versions for "
                                            "%s package." % name)
                        max_version = version
                    elif cls.RE_NE_VERSIONS.match(version):
                        ne_versions.append(version)
                versions = {"min": min_version,
                            "max": max_version,
                            "ne": ne_versions}
            return cls(name, versions)

    def __str__(self):
        if isinstance(self.version, dict):
            version = []

            min_equal_to_max = False
            if self.version["min"] and self.version["max"]:
                if (self.version["min"].startswith(">=") and
                        self.version["max"].startswith("<=") and
                        self.version["min"][2:] == self.version["max"][2:]):
                    # min and max versions are equal there is no need to write
                    # both of them
                    min_equal_to_max = True
                    version.append("==%s" % self.version["min"][2:])

            if not min_equal_to_max and self.version["min"]:
                version.append(self.version["min"])

            if not min_equal_to_max and self.version["ne"]:
                version.extend(self.version["ne"])

            if not min_equal_to_max and self.version["max"]:
                version.append(self.version["max"])

            version = ",".join(version)
        else:
            if self.do_not_touch:
                version = self.version
            else:
                # remove const version
                version = ">=%s" % self.version[2:]

        string = "%s%s" % (self.package_name, version)
        if self.license:
            # NOTE(andreykurilin): When I start implementation of this script,
            #   python-keystoneclient dependency string took around ~45-55
            #   chars, so let's use this length as indent. Feel free to modify
            #   it to lower or greater value.
            magic_number = 55
            if len(string) < magic_number:
                indent = magic_number - len(string)
            else:
                indent = 2
            string += " " * indent + "# " + self.license
        return string

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.package_name == other.package_name)

    def __ne__(self, other):
        return not self.__eq__(other)


def parse_data(raw_data, include_comments=True):
    # first elem is None to simplify checks of last elem in requirements
    requirements = [None]
    for line in raw_data.split("\n"):
        if line.startswith("#"):
            if not include_comments:
                continue

            if getattr(requirements[-1], "is_finished", True):
                requirements.append(Comment())

            requirements[-1].append(line)
        elif line == "":
            # just empty line
            if isinstance(requirements[-1], Comment):
                requirements[-1].finish_him()
            requirements.append(Comment(finished=True))
        else:
            if (isinstance(requirements[-1], Comment) and
                    not requirements[-1].is_finished):
                requirements[-1].finish_him()
            # parse_line
            req = Requirement.parse_line(line)
            if req:
                if (isinstance(requirements[-1], Comment) and
                        DO_NOT_TOUCH_TAG in str(requirements[-1])):
                    req.do_not_touch = True
                requirements.append(req)
    for i in range(len(requirements) - 1, 0, -1):
        # remove empty lines at the end of file
        if isinstance(requirements[i], Comment):
            if str(requirements[i]) == "":
                requirements.pop(i)
        else:
            break
    return requirements[1:]


def _read_requirements():
    """Read all rally requirements."""
    LOG.info("Reading rally requirements...")
    for file_name in RALLY_REQUIREMENTS_FILES:
        LOG.debug("Try to read '%s'." % file_name)
        with open(file_name) as f:
            data = f.read()
        LOG.info("Parsing requirements from %s." % file_name)
        yield file_name, parse_data(data)


def _write_requirements(filename, requirements):
    """Saves requirements to file."""
    LOG.info("Saving requirements to %s." % filename)
    with open(filename, "w") as f:
        for entity in requirements:
            f.write(str(entity))
            f.write("\n")


def _sync():
    LOG.info("Obtaining global-requirements...")
    for i in range(0, len(GLOBAL_REQUIREMENTS_LOCATIONS)):
        url = GLOBAL_REQUIREMENTS_LOCATIONS[i] + GLOBAL_REQUIREMENTS_FILENAME
        LOG.debug("Try to obtain global-requirements from %s" % url)
        try:
            raw_gr = requests.get(url).text
        except requests.ConnectionError as e:
            LOG.exception(e)
            if i == len(GLOBAL_REQUIREMENTS_LOCATIONS) - 1:
                # there are no more urls to try
                raise Exception("Unable to obtain %s" %
                                GLOBAL_REQUIREMENTS_FILENAME)
        else:
            break

    LOG.info("Parsing global-requirements...")
    # NOTE(andreykurilin): global-requirements includes comments which can be
    #   unrelated to Rally project.
    gr = parse_data(raw_gr, include_comments=False)
    for filename, requirements in _read_requirements():
        for i in range(0, len(requirements)):
            if (isinstance(requirements[i], Requirement) and
                    not requirements[i].do_not_touch):
                try:
                    gr_item = gr[gr.index(requirements[i])]
                except ValueError:
                    # it not g-r requirements
                    if isinstance(requirements[i].version, dict):
                        requirements[i].version["max"] = None
                else:
                    requirements[i].version = gr_item.version
        yield filename, requirements


def sync():
    """Synchronizes Rally requirements with OpenStack global-requirements."""
    for filename, requirements in _sync():
        _write_requirements(filename, requirements)


def format_requirements():
    """Obtain package licenses from pypy and write requirements to file."""
    for filename, requirements in _read_requirements():
        _write_requirements(filename, requirements)


def add_uppers():
    """Obtains latest version of packages and put them to requirements."""
    for filename, requirements in _sync():
        LOG.info("Obtaining latest versions of packages from %s." % filename)
        for req in requirements:
            if isinstance(req, Requirement):
                if isinstance(req.version, dict) and not req.version["max"]:
                    req.sync_max_version_with_pypy()
        _write_requirements(filename, requirements)


def main():
    parser = argparse.ArgumentParser(
        prog="Python Requirement Manager for Rally",
        description=__doc__.strip(),
        add_help=True
    )

    action_groups = parser.add_mutually_exclusive_group()
    action_groups.add_argument("--format",
                               action="store_const",
                               const=format_requirements,
                               dest="action")
    action_groups.add_argument("--add-upper",
                               action="store_const",
                               const=add_uppers,
                               dest="action")
    action_groups.set_defaults(action=sync)
    parser.parse_args(sys.argv[1:]).action()

if __name__ == "__main__":
    sys.exit(main())
