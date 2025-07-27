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

from __future__ import annotations

import collections
import datetime as dt
import typing as t
import xml.etree.ElementTree as ET

from rally.common import version


def _prettify_xml(elem: ET.Element, level: int = 0) -> None:
    """Adds indents.

    Code of this method was copied from
        http://effbot.org/zone/element-lib.htm#prettyprint

    """
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            _prettify_xml(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def _filter_attrs(**attrs: t.Any) -> collections.OrderedDict[str, t.Any]:
    return collections.OrderedDict(
        (k, v) for k, v in sorted(attrs.items()) if v is not None)


class _TestCase:
    def __init__(
        self,
        parent: _TestSuite,
        classname: str,
        name: str,
        id: str | None = None,
        time: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        self._parent = parent
        attrs = _filter_attrs(id=id, time=time, classname=classname,
                              name=name, timestamp=timestamp)
        self._elem = ET.SubElement(self._parent._elem, "testcase", **attrs)

    def _add_details(
        self,
        tag: str | None = None,
        text: str | None = None,
        *comments: str | None,
    ) -> None:
        if tag:
            elem = ET.SubElement(self._elem, tag)
            if text:
                elem.text = text
        for comment in comments:
            if comment:
                self._elem.append(ET.Comment(comment))

    def mark_as_failed(self, details: str) -> None:
        self._add_details("failure", details)
        self._parent._increment("failures")

    def mark_as_uxsuccess(self, reason: str | None = None) -> None:
        # NOTE(andreykurilin): junit doesn't support uxsuccess
        #   status, so let's display it like "fail" with proper comment.
        self.mark_as_failed(
            f"It is an unexpected success. The test "
            f"should fail due to: {reason or 'Unknown reason'}"
        )

    def mark_as_xfail(
        self,
        reason: str | None = None,
        details: str | None = None,
    ) -> None:
        reason = (f"It is an expected failure due to: "
                  f"{reason or 'Unknown reason'}")
        self._add_details(None, None, reason, details)

    def mark_as_skipped(self, reason: str | None) -> None:
        self._add_details("skipped", reason or "Unknown reason")
        self._parent._increment("skipped")


class _TestSuite:
    def __init__(
        self,
        parent: ET.Element,
        id: str,
        time: str,
        timestamp: str,
    ) -> None:
        self._parent = parent
        attrs = _filter_attrs(id=id, time=time, tests="0",
                              errors="0", skipped="0",
                              failures="0", timestamp=timestamp)
        self._elem = ET.SubElement(self._parent, "testsuite", **attrs)

        self._finalized = False
        self._calculate = True
        self._total = 0
        self._skipped = 0
        self._failures = 0

    def _finalize(self) -> None:
        if not self._finalized and self._calculate:
            self._setup_final_stats(tests=str(self._total),
                                    skipped=str(self._skipped),
                                    failures=str(self._failures))
        self._finalized = True

    def _setup_final_stats(
        self,
        tests: str,
        skipped: str,
        failures: str,
    ) -> None:
        self._elem.set("tests", tests)
        self._elem.set("skipped", skipped)
        self._elem.set("failures", failures)

    def setup_final_stats(
        self,
        tests: str,
        skipped: str,
        failures: str,
    ) -> None:
        """Turn off calculation of final stats."""
        self._calculate = False
        self._setup_final_stats(tests, skipped, failures)

    def _increment(self, status: str) -> None:
        if self._calculate:
            key = f"_{status}"
            value = getattr(self, key) + 1
            setattr(self, key, value)
            self._finalized = False

    def add_test_case(
        self,
        classname: str,
        name: str,
        id: str | None = None,
        time: str | None = None,
        timestamp: str | None = None,
    ) -> _TestCase:
        self._increment("total")
        return _TestCase(self, id=id, classname=classname, name=name,
                         time=time, timestamp=timestamp)


class JUnitXML:
    """A helper class to build JUnit-XML report without knowing XML."""

    def __init__(self) -> None:
        self._root = ET.Element("testsuites")
        self._test_suites: list[_TestSuite] = []

        self._root.append(
            ET.Comment("Report is generated by Rally %s at %s" % (
                version.version_string(),
                dt.datetime.utcnow().isoformat()))
        )

    def __str__(self) -> str:
        return self.to_string()

    def to_string(self) -> str:
        for test_suite in self._test_suites:
            test_suite._finalize()

        _prettify_xml(self._root)

        return ET.tostring(self._root, encoding="utf-8").decode("utf-8")

    def add_test_suite(
        self,
        id: str,
        time: str,
        timestamp: str,
    ) -> _TestSuite:
        test_suite = _TestSuite(
            self._root, id=id, time=time, timestamp=timestamp)
        self._test_suites.append(test_suite)
        return test_suite
