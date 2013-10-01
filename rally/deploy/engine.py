# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import abc

from rally import consts
from rally import exceptions
from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging
from rally import utils

LOG = logging.getLogger(__name__)


class EngineFactory(object):
    """rally.deploy.engine.EngineFactory is base class for every engine.

    All engines should be added to rally.deploy.engines.some_module.py

    Example of usage:

    # Add new engine with __name__ == 'A'
    class A(EngineFactory):
        def __init__(self, config):
            # do something

        def deploy(self):
            # Do deployment and return endpoints of openstack
            return {}   # here should be endpoints

        def cleanup(self):
            # Destory OpenStack deployment and free resource

    Now to use new engine 'A' we should use with statement:

    with EngineFactory.get_engine('A', some_config) as deployment:
        # deployment is returned value of deploy() method
        # do all stuff that you need with your cloud
    """
    __metaclass__ = abc.ABCMeta

    @staticmethod
    def get_engine(name, task, config):
        """Returns instance of deploy engine with corresponding name."""
        task_uuid = task['uuid']
        LOG.info(_('Task %(uuid)s: Creating the deploy engine for '
                   '%(name)s...') % {'uuid': task_uuid, 'name': name})
        for engine in utils.itersubclasses(EngineFactory):
            if name == engine.__name__:
                new_engine = engine(task, config)
                LOG.info(_('Task %(uuid)s: Deploy engine for %(name)s '
                           'successfully created.') %
                         {'uuid': task_uuid, 'name': name})
                return new_engine
        LOG.exception(_('Task %(uuid)s: Deploy engine for %(name)s '
                        'does not exist.') % {'uuid': task_uuid, 'name': name})
        raise exceptions.NoSuchEngine(engine_name=name)

    @staticmethod
    def get_available_engines():
        """Returns list of names of available engines."""
        return [e.__name__ for e in utils.itersubclasses(EngineFactory)]

    @abc.abstractmethod
    def deploy(self):
        """Deploy OpenStack cloud and return endpoints."""

    @abc.abstractmethod
    def cleanup(self):
        """Cleanup OpenStack deployment."""

    def make(self):
        task_uuid = self.task['uuid']
        LOG.info(_('Task %s: Starting the deployment...') % task_uuid)
        self.task.update_status(consts.TaskStatus.DEPLOY_STARTED)
        endpoints = self.deploy()
        LOG.info(_('Task %s: Deployment completed.') % task_uuid)
        self.task.update_status(consts.TaskStatus.DEPLOY_FINISHED)
        return endpoints

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        task_uuid = self.task['uuid']
        if type:
            LOG.exception(_('Task %(uuid)s: Error: %(msg)s') %
                          {'uuid': task_uuid, 'msg': value.message})
            self.task.set_failed()
        LOG.info(_('Task %s: Starting cleanup...') % task_uuid)
        self.task.update_status(consts.TaskStatus.CLEANUP)
        try:
            self.cleanup()
        except Exception:
            LOG.exception(_('Task %s: Cleanup failed.') % task_uuid)
            self.task.set_failed()
            raise
        finally:
            self.task.update_status(consts.TaskStatus.FINISHED)
        LOG.info(_('Task %s: Cleanup completed.') % task_uuid)
