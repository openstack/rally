# Copyright 2014: Mirantis Inc.
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

import pecan
from wsme import types as wtypes


class Link(wtypes.Base):
    """A link representation."""

    href = wtypes.text
    rel = wtypes.text
    type = wtypes.text

    @classmethod
    def make_link(cls, rel, url, resource, type=wtypes.Unset):
        href = "{url}/{resource}".format(url=url, resource=resource)
        return cls(href=href, rel=rel, type=type)


class MediaType(wtypes.Base):
    """A media type representation."""

    base = wtypes.text
    type = wtypes.text

    def __init__(self, base, type):
        self.base = base
        self.type = type


class Version(wtypes.Base):
    """A version type representations."""

    id = wtypes.text
    status = wtypes.text
    updated_at = wtypes.text
    media_types = [MediaType]
    links = [Link]

    @classmethod
    def convert(cls, id, status, updated_at=None, media_types=None,
                links=None):
        v = Version(id=id, status=status, updated_at=updated_at)
        if media_types is None:
            mime_type = "application/vnd.openstack.rally.%s+json" % id
            media_types = [MediaType("application/json", mime_type)]
        v.media_types = media_types
        if links is None:
            links = [Link.make_link("self", pecan.request.host_url, id)]
        v.links = links
        return v
