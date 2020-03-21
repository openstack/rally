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


def _join_keys(first, second):
    if not second:
        return first
    elif second.startswith("["):
        return "%s%s" % (first, second)
    else:
        return "%s.%s" % (first, second)


def _process(obj):
    if isinstance(obj, (str, bytes)):
        yield "", obj
    elif isinstance(obj, dict):
        for first, tmp_value in obj.items():
            for second, value in _process(tmp_value):
                yield _join_keys(first, second), value
    elif isinstance(obj, (list, tuple)):
        for i, tmp_value in enumerate(obj):
            for second, value in _process(tmp_value):
                yield _join_keys("[%s]" % i, second), value
    else:
        try:
            yield "", "%s" % obj
        except Exception:
            raise ValueError("Cannot transform obj of '%s' type to flatten "
                             "structure." % type(obj))


def transform(obj):
    """Transform object to a flatten structure.

    Example:
        IN:
            {"foo": ["xxx", "yyy", {"bar": {"zzz": ["Hello", "World!"]}}]}
        OUTPUT:
            [
                "foo[0]=xxx",
                "foo[1]=yyy",
                "foo[2].bar.zzz[0]=Hello",
                "foo[2].bar.zzz[1]=World!"
            ]

    """
    result = []
    for key, value in _process(obj):
        if key:
            result.append("%s=%s" % (key, value))
        else:
            result.append(value)
    return sorted(result)
