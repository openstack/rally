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
import os

from rally import consts
from rally.plugins.common.verification import testr
from rally.verification import manager


@manager.configure(name="installation", platform="fakeverifier",
                   default_repo="https://opendev.org/openstack/rally",
                   context={"testr": {}})
class FakeVerifierInstallation(testr.TestrLauncher):
    """FakeVerify verifier."""

    def install(self):
        super(FakeVerifierInstallation, self).install()
        # use stestr for tests.
        with open(os.path.join(self.repo_dir, ".stestr.conf"), "w") as f:
            f.write("[DEFAULT]\ntest_path=./tests/unit")
        print("fakeverify was installed successfully.")


@manager.configure(name="extension", platform="fakeverifier")
class FakeVerifierExtension(testr.TestrLauncher):
    def install(self):
        pass

    def install_extension(self, source, version=None, extra_settings=None):
        if source != "fake_url":
            raise Exception("Failed to pass source argument.")
        if (self.verifier.status != consts.VerifierStatus.EXTENDING):
            raise Exception("Failed to update the status.")

    def list_extensions(self):
        return [{"name": "fake_extension", "entry_point": "fake_entrypoint"}]

    def uninstall_extension(self, name):
        if name != "fake_extension":
            raise Exception("Failed to uninstall extension.")
        print("uninstalled extension successfully.")
