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

from rally import log as logging


def setup_app(config):
    """Initialize Pecan application.

    This is a generic interface method of an application.

    :param config: An instance of :class:`pecan.Config`.
    :return: A normal WSGI application, an instance of
             :class:`pecan.Pecan`.
    """
    app = pecan.Pecan(config.app.root, debug=logging.is_debug())
    return app


def make_app():
    config = {
        "app": {
            "root": "rally.aas.rest.controllers.root.RootController",
            "modules": ["rally.aas.rest"],
            "debug": logging.is_debug(),
        },
        "wsme": {
            "debug": logging.is_debug(),
        },
    }
    app = pecan.load_app(config)
    return app
