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
import jsonschema

from rally import consts
from rally import exceptions
from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging
from rally import utils


LOG = logging.getLogger(__name__)


class EngineFactory(object):
    """Base class of all deployment engines.

    It's a base class with self-discovery of subclasses. Each a subclass
    have to implement deploy and cleanup methods. By default each engine
    that located as a submodule of the package rally.deploy.engines is
    auto-discovered.

    Example of usage with a simple engine:

    # Add new engine with __name__ == 'A'
    class A(EngineFactory):
        def __init__(self, deployment):
            # do something

        def deploy(self):
            # Do deployment and return endpoint of openstack
            return {}   # here should be endpoint

        def cleanup(self):
            # Destory OpenStack deployment and free resource

    An instance of this class used as a context manager on any unsafe
    operations to a deployment. Any unhandled exceptions bring a status
    of the deployment to the inconsistent state.

    with EngineFactory.get_engine('A', deployment) as deploy:
        # deploy is an instance of the A engine
        # perform all usage operations on your cloud
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, deployment):
        self.deployment = deployment
        self.config = deployment['config']
        self.validate()

    def validate(self):
        # TODO(sskripnick): remove this checking when config schema
        # is done for all available engines
        if hasattr(self, 'CONFIG_SCHEMA'):
            jsonschema.validate(self.config, self.CONFIG_SCHEMA)

    @staticmethod
    def get_engine(name, deployment):
        """Returns instance of a deploy engine with corresponding name."""
        for engine in utils.itersubclasses(EngineFactory):
            if name == engine.__name__:
                new_engine = engine(deployment)
                return new_engine
        LOG.error(_('Deployment %(uuid)s: Deploy engine for %(name)s '
                    'does not exist.') %
                  {'uuid': deployment['uuid'], 'name': name})
        deployment.update_status(consts.DeployStatus.DEPLOY_FAILED)
        raise exceptions.NoSuchEngine(engine_name=name)

    @staticmethod
    def get_available_engines():
        """Returns a list of names of available engines."""
        return [e.__name__ for e in utils.itersubclasses(EngineFactory)]

    @abc.abstractmethod
    def deploy(self):
        """Deploy OpenStack cloud and return an endpoint."""

    @abc.abstractmethod
    def cleanup(self):
        """Cleanup OpenStack deployment."""

    @utils.log_deploy_wrapper(LOG.info, _("OpenStack cloud deployment."))
    def make_deploy(self):
        self.deployment.update_status(consts.DeployStatus.DEPLOY_STARTED)
        endpoint = self.deploy()
        self.deployment.update_status(consts.DeployStatus.DEPLOY_FINISHED)
        return endpoint

    @utils.log_deploy_wrapper(LOG.info,
                              _("Destroy cloud and free allocated resources."))
    def make_cleanup(self):
        self.deployment.update_status(consts.DeployStatus.CLEANUP_STARTED)
        self.cleanup()
        self.deployment.update_status(consts.DeployStatus.CLEANUP_FINISHED)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is not None:
            LOG.error(_("Deployment %(uuid)s: Error was occurred into context "
                        "of the deployment"),
                      {'uuid': self.deployment['uuid']},
                      exc_info=(exc_type, exc_value, exc_traceback))
            status = self.deployment['status']
            if status in (consts.DeployStatus.DEPLOY_INIT,
                          consts.DeployStatus.DEPLOY_STARTED):
                self.deployment.update_status(
                    consts.DeployStatus.DEPLOY_FAILED)
            elif status == consts.DeployStatus.DEPLOY_FINISHED:
                self.deployment.update_status(
                    consts.DeployStatus.DEPLOY_INCONSISTENT)
            elif status == consts.DeployStatus.CLEANUP_STARTED:
                self.deployment.update_status(
                    consts.DeployStatus.CLEANUP_FAILED)
