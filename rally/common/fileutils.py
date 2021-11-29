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

import os
import tempfile
import warnings
import zipfile


warnings.warn(
    f"Module `{__name__}` is deprecated since Rally v3.0.0 and may be "
    f"removed in further releases."
)


def pack_dir(source_directory, zip_name=None):
    """Archive content of the directory into .zip

    Zip content of the source folder excluding root directory
    into zip archive. When zip_name is specified, it would be used
    as a destination for the archive. Otherwise method would
    try to use temporary file as a destination for the archive.

    :param source_directory: root of the newly created archive.
        Directory is added recursively.
    :param zip_name: destination zip file name.
    :raises IOError: whenever there are IO issues.
    :returns: path to the newly created zip archive either specified via
        zip_name or a temporary one.
    """

    if not zip_name:
        fp = tempfile.NamedTemporaryFile(delete=False)
        zip_name = fp.name
    zipf = zipfile.ZipFile(zip_name, mode="w")
    try:
        for root, dirs, files in os.walk(source_directory):
            for f in files:
                abspath = os.path.join(root, f)
                relpath = os.path.relpath(abspath, source_directory)
                zipf.write(abspath, relpath)
    finally:
        zipf.close()
    return zip_name
