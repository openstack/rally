..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

..
 This template should be in ReSTructured text. The filename in the git
 repository should match the launchpad URL, for example a URL of
 https://blueprints.launchpad.net/heat/+spec/awesome-thing should be named
 awesome-thing.rst .  Please do not delete any of the sections in this
 template.  If you have nothing to say for a whole section, just write: None
 For help with syntax, see http://sphinx-doc.org/rest.html
 To test out your formatting, see http://www.tele3.cz/jbar/rest/rest.html


=================================
Rally Task Validation Refactoring
=================================

Problem description
===================

* Current validator system is pluggable - but it doesn't use our plugin
  mechanism which creates problems (e.g. validators are imported directly and
  used in code, instead of using their names, which doesn't allow to rename
  them or move without breaking backward compatibility).

* Current mechanism of validation leads to a lot of OpenStack related code in
  the Rally task engine.

* It's hard to use the same validators for different types of plugins, current
  approach is used only for scenarios.

Proposed change
===============

To create unified validation mechanism that can be used for all types of
future deployments and type of plugins in the same way. So we will be able
to remove `OpenStack related code <https://github
.com/openstack/rally/blob/be8cd7bff6de9b3e83dd31005ae5d07ca1c86b9e/rally
/task/engine.py#L188-L278>`_ from the task engine, and create a bunch of
common validators (e.g. jsonschema) that can be used by any
plugin.
As a bonus of refactoring, it allows us to switch to common mechanism of
plugins.

Alternatives
------------

No way


Implementation
==============

Here is an example of base class for all pluggable validators.

.. code-block:: python

    import abc
    import six

    from rally.common.plugin import plugin
    from rally.task import validation


    def configure(name, namespace="default"):
        return plugin.configure(name=name, namespace=namespace)

    @six.add_metaclass(abc.ABCMeta)
    @configure(name="base_validator")
    class Validator(plugin.Plugin):

        def validate(self, cache, deployment, cfg, plugin_cfg):
            """
            Method that validates something.

            :param cache: this is cross validator cache where different
                          validators could store information about
                          environment like initialized OpenStack clients,
                          images, etc and share it through validators.
                          E.g. if your custom validators need to perform 200
                          OpenStack checks and each validator plugin need to
                          initialize client, Rally will take extra 2 minutes
                          for validation step. As well, its not efficient to
                          fetch all image each time if we have image related
                          validators.
            :param deployment: Deployment object, deployment which would be
                               used for validation
            :param cfg: dict, configuration of subtask
            :param plugin_cfg: dict, with exact configuration of the plugin
            """
            pass

    def add(name, **kwargs):
        """
        Add validator instance to the validator plugin class meta.

        Get validator class by name. Initialize an instance. Add validator
        instance to validators list stored in the Validator meta by
        'validator_v2' key. This would be used to iterate and execute through
        all validators used during execution of subtask.

        :param kwargs: dict, arguments used to initialize validator class
                      instance
        :param name: str, name of the validator plugin
        """
        validator = Validator.get(name)(**kwargs)

        def wrapper(p):
            p._meta_setdefault("validators_v2", [])
            p._meta_get("validators_v2").append(validator)
            return p

        return wrapper


    @abc.abstractmethod
    def validate(plugin, deployment, cfg, plugin_cfg):
        """
        Execute all validate() method of all validators stored in meta of
        Validator.

        Iterate during all validators stored in the meta of Validator and
        execute proper validate() method and add validation result to the
        list.

        :param plugin: is plugin class instance that has validators and should
                       be validated
        :param deployment: Deployment object, deployment which would be
                           used for validation
        :param cfg: dict, configuration of subtask
        :param plugin_cfg: dict, with exact configuration of the plugin
        """
        results = []
        cache = {}

        for v in plugin._meta_get("validators_v2"):
            try:
                v.validate(cache, deployment, cfg, plugin_cfg)
            except Exception as e:
                results.append(validation.ValidationResult(is_valid=False,
                                                           msg=e))
        return results


New design allows us to use the same validator and same validation mechanism
for different types of plugins (context, sla, runner, scenarios) which was not
possible before. For example, we could implement jsonschema validation as a
plugin.

.. code-block:: python

    import jsonschema

    @configure(name="jsonschema")
    class JsonSchemaValidator(Validator):

        def __init__(self, schema=None):
            super(JsonSchemaValidator, self).__init__()
            self.schema = schema or {}

        def validate(self, cache, deployment, cfg, plugin_cfg):
            jsonschema.validate(plugin_cfg, self.schema)



    @validator.add("jsonschema", schema="<here_json_schema>")
    class SomeContext(base.Context):
        pass


    class SomeScenario(base.Scenario):

        @validator.add("jsonschema", schema="<here_json_schema>")
        def some_function(self):
            pass


Assignee(s)
-----------

Primary assignee:

- boris-42 <bpavlovic@mirantis.com>
- rvasilets <rvasilets@mirantis.com>

Work Items
----------

- Create validation module with base plugin and method of adding validators

- Add support to task engine of new validation mechanism

- Port all old validators to new mechanism

- Deprecate old validation mechanism

- Remove deprecated in new release


Dependencies
============

None
