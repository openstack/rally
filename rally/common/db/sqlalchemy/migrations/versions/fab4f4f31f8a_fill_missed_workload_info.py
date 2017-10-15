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

"""fix-statistics-of-workloads

Absorbed by 4394bdc32cfd_fill_missed_workload_info_r3

Revision ID: fab4f4f31f8a
Revises: e0a5df2c5153
Create Date: 2017-08-30 18:00:12.811614

"""

from rally import exceptions

# revision identifiers, used by Alembic.
revision = "fab4f4f31f8a"
down_revision = "e0a5df2c5153"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    raise exceptions.DowngradeNotSupported()
