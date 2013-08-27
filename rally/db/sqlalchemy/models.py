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
"""
SQLAlchemy models for rally data.
"""
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
import uuid

from rally import consts
from rally.openstack.common.db.sqlalchemy import models
from rally.openstack.common.db.sqlalchemy import session


BASE = declarative_base()


class RallyBase(models.SoftDeleteMixin,
                models.TimestampMixin,
                models.ModelBase):
    metadata = None


def create_db():
    drop_db()
    BASE.metadata.create_all(session.get_engine())


def drop_db():
    engine = session.get_engine()
    OLD_BASE = declarative_base()
    OLD_BASE.metadata.reflect(bind=engine)
    OLD_BASE.metadata.drop_all(engine, checkfirst=True)
