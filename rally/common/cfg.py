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

# NOTE(andreykurilin): In near future we are planning to get rid of
#   oslo_config. As a first step, let's hardcode the interface of it

from oslo_config import cfg
from oslo_config import fixture  # noqa


CONF = cfg.CONF
ConfigOpts = cfg.ConfigOpts

find_config_dirs = cfg.find_config_dirs
find_config_files = cfg.find_config_files
set_defaults = cfg.set_defaults

# exceptions
ArgsAlreadyParsedError = cfg.ArgsAlreadyParsedError
ConfigDirNotFoundError = cfg.ConfigDirNotFoundError
ConfigFileParseError = cfg.ConfigFileParseError
ConfigFileValueError = cfg.ConfigFileValueError
ConfigFilesNotFoundError = cfg.ConfigFilesNotFoundError
ConfigFilesPermissionDeniedError = cfg.ConfigFilesPermissionDeniedError
DefaultValueError = cfg.DefaultValueError
DuplicateOptError = cfg.DuplicateOptError
Error = cfg.Error
NoSuchGroupError = cfg.NoSuchGroupError
NoSuchOptError = cfg.NoSuchOptError
NotInitializedError = cfg.NotInitializedError
ParseError = cfg.ParseError
RequiredOptError = cfg.RequiredOptError
TemplateSubstitutionError = cfg.TemplateSubstitutionError

# option types
Opt = cfg.Opt
OptGroup = cfg.OptGroup
BoolOpt = cfg.BoolOpt
DeprecatedOpt = cfg.DeprecatedOpt
DictOpt = cfg.DictOpt
FloatOpt = cfg.FloatOpt
HostAddressOpt = cfg.HostAddressOpt
HostnameOpt = cfg.HostnameOpt
IPOpt = cfg.IPOpt
IntOpt = cfg.IntOpt
ListOpt = cfg.ListOpt
MultiOpt = cfg.MultiOpt
MultiStrOpt = cfg.MultiStrOpt
PortOpt = cfg.PortOpt
StrOpt = cfg.StrOpt
SubCommandOpt = cfg.SubCommandOpt
URIOpt = cfg.URIOpt
