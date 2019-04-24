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

import collections
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
    "http://opendev.org/openstack/requirements/raw/branch/master/"
)
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


_PYPI_CACHE = {}


class PYPIPackage(object):
    # NOTE(andreykurilin): one license can have different labels. Let's use
    #   unified variant.
    LICENSE_MAP = {"MIT license": "MIT",
                   "MIT License": "MIT",
                   "BSD License": "BSD",
                   "Apache 2.0": "Apache License, Version 2.0"}

    def __init__(self, package_name):
        self.package_name = package_name
        self._pypi_info = None
        self._pypi_license = None

    @property
    def pypi_info(self):
        if self._pypi_info is None:
            if self.package_name in _PYPI_CACHE:
                self._pypi_info = _PYPI_CACHE[self.package_name]
            else:
                resp = requests.get("https://pypi.org/pypi/%s/json" %
                                    self.package_name)
                if resp.status_code != 200:
                    print("An error occurred while checking '%s' package at "
                          "pypi." % self.package_name)
                    raise Exception(resp.text)
                self._pypi_info = resp.json()

                # let's cache it for the case when we need to sync requirements
                # and update upper constrains
                _PYPI_CACHE[self.package_name] = self._pypi_info
        return self._pypi_info

    @property
    def pypi_version(self):
        return self.pypi_info["info"]["version"]

    @property
    def pypi_license(self):
        if self._pypi_license is None:
            if self.pypi_info["info"]["license"]:
                self._pypi_license = self.pypi_info["info"]["license"]
            else:
                # try to parse classifiers
                prefix = "License :: OSI Approved :: "
                classifiers = [c[len(prefix):]
                               for c in self.pypi_info["info"]["classifiers"]
                               if c.startswith(prefix)]
                self._pypi_license = "/".join(classifiers)
            self._license = self.LICENSE_MAP.get(self._pypi_license,
                                                 self._pypi_license)
            if self._pypi_license == "UNKNOWN":
                self._pypi_license = None
        return self._license

    def __eq__(self, other):
        return (isinstance(other, PYPIPackage) and
                self.package_name == other.package_name)


class Requirement(PYPIPackage):
    RE_NAME = re.compile(r"[a-zA-Z0-9-._]+")
    RE_CONST_VERSION = re.compile(r"==[a-zA-Z0-9.]+")
    RE_MIN_VERSION = re.compile(r">=?[a-zA-Z0-9.]+")
    RE_MAX_VERSION = re.compile(r"<=?[a-zA-Z0-9.]+")
    RE_NE_VERSIONS = re.compile(r"!=[a-zA-Z0-9.]+")

    def __init__(self, package_name, version):
        super(Requirement, self).__init__(package_name)
        self.version = version
        self.do_not_touch = False

    def sync_max_version_with_pypy(self):
        if isinstance(self.version, dict) and not self.do_not_touch:
            self.version["max"] = "<=%s" % self.pypi_version

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
        if self.pypi_license:
            # NOTE(andreykurilin): When I start implementation of this script,
            #   python-keystoneclient dependency string took around ~45-55
            #   chars, so let's use this length as indent. Feel free to modify
            #   it to lower or greater value.
            magic_number = 55
            if len(string) < magic_number:
                indent = magic_number - len(string)
            else:
                indent = 2
            string += " " * indent + "# " + self.pypi_license
        return string

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.package_name == other.package_name)

    def __ne__(self, other):
        return not self.__eq__(other)


class UpperConstraint(PYPIPackage):

    RE_LINE = re.compile(
        r"(?P<package_name>[a-zA-Z0-9-._]+)===(?P<version>[a-zA-Z0-9.]+)")

    def __init__(self, package_name, version=None):
        super(UpperConstraint, self).__init__(package_name)
        self._version = version

    def __str__(self):
        return "%s===%s" % (self.package_name, self.version)

    @property
    def version(self):
        if self._version is None:
            self._version = self.pypi_version
        return self._version

    @classmethod
    def parse_line(cls, line):
        match = cls.RE_LINE.match(line)
        if match:
            return cls(**match.groupdict())

    def update(self, version):
        self._version = version


def parse_data(raw_data, include_comments=True, dependency_cls=Requirement):
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
            dep = dependency_cls.parse_line(line)
            if dep:
                if (isinstance(requirements[-1], Comment) and
                        DO_NOT_TOUCH_TAG in str(requirements[-1])):
                    dep.do_not_touch = True
                requirements.append(dep)

    for i in range(len(requirements) - 1, 0, -1):
        # remove empty lines at the end of file
        if isinstance(requirements[i], Comment):
            if str(requirements[i]) == "":
                requirements.pop(i)
        else:
            break
    return collections.OrderedDict(
        (v if isinstance(v, Comment) else v.package_name, v)
        for v in requirements if v)


def _fetch_from_gr(filename):
    """Try to fetch data from OpenStack global-requirements repo"""
    for i in range(0, len(GLOBAL_REQUIREMENTS_LOCATIONS)):
        url = GLOBAL_REQUIREMENTS_LOCATIONS[i] + filename
        LOG.debug("Try to obtain %s from %s" % (filename, url))
        try:
            return requests.get(url).text
        except requests.ConnectionError as e:
            LOG.exception(e)
    raise Exception("Unable to obtain %s" % filename)


def _write_requirements(filename, requirements):
    """Saves requirements to file."""
    if isinstance(requirements, dict):
        requirements = requirements.values()
    LOG.info("Saving requirements to %s." % filename)
    with open(filename, "w") as f:
        for entity in requirements:
            f.write(str(entity))
            f.write("\n")


def sync_requirements():
    """Synchronizes Rally requirements with OpenStack global-requirements."""
    LOG.info("Obtaining global-requirements of OpenStack...")
    raw_gr = _fetch_from_gr("global-requirements.txt")

    # NOTE(andreykurilin): global-requirements includes comments which can be
    #   unrelated to Rally project, so let's just ignore them
    gr = parse_data(raw_gr, include_comments=False)
    for file_name in RALLY_REQUIREMENTS_FILES:
        LOG.debug("Processing '%s'." % file_name)
        with open(file_name) as f:
            requirements = parse_data(f.read())
        for name, req in requirements.items():
            if isinstance(req, Requirement) and not req.do_not_touch:
                if name in gr:
                    req.version = gr[req.package_name].version
                else:
                    # it not g-r requirements
                    if isinstance(req.version, dict):
                        req.version["max"] = None
        _write_requirements(file_name, requirements)


def update_upper_constraints():
    """Obtains latest version of packages and put them to upper-constraints."""
    LOG.info("Obtaining upper-constrains from OpenStack...")
    raw_g_uc = _fetch_from_gr("upper-constraints.txt")
    # NOTE(andreykurilin): global OpenStack upper-constraints file includes
    #   comments which can be unrelated to Rally project, so let's just ignore
    #   them.
    global_uc = parse_data(raw_g_uc,
                           include_comments=False,
                           dependency_cls=UpperConstraint)
    with open("upper-constraints.txt") as f:
        our_uc = parse_data(f.read(),
                            dependency_cls=UpperConstraint)
    with open("requirements.txt") as f:
        our_requirements = parse_data(f.read(), include_comments=False)

    for name, req in our_requirements.items():
        if isinstance(req, Comment):
            continue
        if name not in our_uc:
            our_uc[name] = UpperConstraint(name)

        if name in global_uc:
            # we cannot use whatever we want versions in CI. OpenStack CI
            # ignores versions listed in requirements of
            # particular project and use versions from global u-c file.
            # It means that we need to suggest to use the same versions
            our_uc[name].update(global_uc[name].version)

    our_uc = sorted(our_uc.values(), key=lambda o: o.package_name.upper())
    _write_requirements("upper-constraints.txt", our_uc)


def main():
    sync_requirements()
    update_upper_constraints()


if __name__ == "__main__":
    sys.exit(main())
