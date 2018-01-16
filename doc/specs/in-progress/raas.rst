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
 For help with syntax, see http://www.sphinx-doc.org/en/stable/rest.html
 To test out your formatting, see http://www.tele3.cz/jbar/rest/rest.html

==================
Rally-as-a-Service
==================

Problem description
===================

Having Rally Web Service that gives access to Rally functionality via HTTP is a
highly desired feature.

Proposed change
===============

Enhance Rally API
-----------------

Using Rally as a library (python client) seems to be a convenient way to
automate its usage in different applications. The full power of Rally, however,
can be now accessed only through its command-line interface.
The current Rally API is not powerful enough to be used for Rally-as-a-Service.

Move all features from CLI to API
"""""""""""""""""""""""""""""""""

Rally API should provide the same features which are available in CLI.

To achieve that all direct DB calls and Rally objects should be removed from
CLI layer. The CLI implementation should be restricted to pure API method
calls, and the API should cover all stuff that is needed for CLI (processing
results, making reports, etc.).

Make API return serializable objects
""""""""""""""""""""""""""""""""""""

Rally API should always return something that can be easily serialized and sent
over HTTP. It is required change, since we do not want to duplicate code which
is used by CLI and which will be used by Rally-as-a-Service. Both of these
entities should wrap the same thing - Rally API.

Move from a classmethod model to a instancemethod model in the API
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Each of API method should not be a single function - classmethod.
The instancemethod model should establish a right way of communication between
different API methods and provide an access to API preferences.

Also, it would be nice to create a base class for single API group.

  .. code-block:: python

    class APIGroup(object):
        def __init__(self, api):
            """Initialize API group.

            :param api: an instance of rally.api.API object
            """
            self.api = api

    class _Task(APIGroup):
        def start(self, deployment, config, task=None,
                  abort_on_sla_failure=False):
            deployment = self.api.deployment._get(deployment)

            ...


Wrap each API method
""""""""""""""""""""

Since usage of the API via HTTP should be similar to the direct usage, we need
to wrap each of API methods by the specific decorator which will decide to send
a http request or make a direct call to the API.

  .. code-block:: python

    from rally import exceptions

    def api_wrapper(path, method):
        def decorator(func)
            def inner(self, *args, **kwargs):
                if args:
                    raise TypeError("It is restricted to use positional
                        arguments for API calls.")

                if self.api.endpoint_url:
                    # it's a call to the remote Rally instance
                    return self._request(path, method, **kwargs)
                else:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        # NOTE(andreykurilin): we need to use the same error
                        #   handling things as it is done in dispatcher, so
                        #   one error will have the same representation in
                        #   both cases - via direct use and via HTTP
                        raise exceptions.make_exception(e)


            inner.path = path
            inner.method = method

            return inner
        return decorator


The specific ``_request`` method for handling all communication details,
serialization and errors should be implemented in the common class APIGroup.

  .. code-block:: python

    import collections
    import requests

    from rally import exceptions

    class APIGroup(object):

        def _request(self, path, method, **kwargs):
            response = request.request(method, path, json=kwargs)
            if response.status_code != 200:
                raise exceptions.find_exception(response)

            # use OrderedDict by default for all cases
            return response.json(
                object_pairs_hook=collections.OrderedDict)["result"]


Rally-as-a-Service implementation
---------------------------------

The code base of Rally-as-a-Service should be located in ``rally.aas`` module.

The application should discover all API methods and check their properties to
identify methods that should be available via HTTP.

  .. code-block:: python

    from rally import api

    def discover_routes(rapi):
        """

        :param rapi: an instance of rally.api.API
        """

        routes = []
        for group, obj in vars(rapi)):
            if not isinstance(obj, APIGroup):
                continue

            for name, method in vars(obj):
                if name.startswith("_"):
                    # do not touch private methods
                    continue
                if hasattr(method, "path") and hasattr(method, "method"):
                    routes.append({"path": "%s/%s" % (group, method.path),
                                   "method": method.method,
                                   "handler": method})
        return routes


Since we have custom data, errors and etc, we need custom preparation method
too.

  .. code-block:: python

    import json

    def dispatch(func, kwargs):
        """
        :param func: method to call
        """
        response = {}
        status_code = 200
        try:
            response["result"] = func(**kwargs)
        except Exception as e:
            status_code = getattr(e, "http_code", 500)
            response["error"] = {"name": e.__name__,
                                 "msg": str(e),
                                 "args": getattr(a, args)}
        return json.dumps(response, sort_keys=False), status_code



Most of the routing and dispatching things will be done via our specific
methods and decorators, so our requirements to web framework are simple - we do
not need much from it.

Let's start from `Flask <http://flask.pocoo.org/>`_ web framework. It is quite
simple, lightweight and compatible with WSGI. In future, it should not be too
difficult to switch from it.

Since there are a lot of blocking calls in Rally, only read-only methods (
"GET" method type) should be allowed at first implementation of
Rally-as-a-Service.

  .. code-block:: python

    import flask


    class Application(object):

        API_PATH_TEMPLATE = "/api/v%(version)s/%(path)s"

        def __init__(self, rapi):
            self.rapi = rapi
            self.app  = flask.Flask("OpenStack Rally")
            self.app.add_url_rule("<path:path>", methods=["GET"],
                view_func=self)
            self._routes = dict(
                [(PATH_TEMPLATE % {"version": rapi.get_api_version(),
                                   "path": path}, handler)
                 for path, handler in discover_routes().items()])

        def __call__(self, path):
            if path not in self._routes:
                # redirect to 404
            return dispatch(self._routes[path], flask.request.data)


        def start(self, ip, port):
            self.app.start(ip, port)


Routing convention
""""""""""""""""""

The routes for each API method should match next format:

    ``/api/v<VERSION_OF_API>/<API_GROUP>/<METHOD_NAME>``

, where

* ``<VERSION_OF_API>`` is a version of API. We do not provide versioning of
  API, so let's put "1" for now.
* ``<API_GROUP>`` can be task, deployment, verification and etc
* ``<METHOD_NAME>`` should represent the name of method to call.

Example of possible path: ``/api/v1/task/validate``

Exception refactoring
---------------------

To make existing exception classes from ``rally.exceptions`` module usable in
case of RaaS, they should:

* store initialization arguments, so it will be possible to re-create object
* contain error code as a property.

Serialization/De-serialization of exceptions
""""""""""""""""""""""""""""""""""""""""""""

Exceptions should serializable as other return data. Serialization mechanism is
described with ``dispatch`` method.

De-serialization should look like:

  .. code-block:: python

    exception_map = dict((e.error_code, e)
                         for e in RallyException.subclasses())

    def find_exception(response):
        """Discover a proper exception class based on response object"""
        exc_class = exception_map.get(response.status_code, RallyException)
        error_data = response.json()["error"]
        if error_data["args"]:
            return exc_class(error_data["args"])
        return exc_class(error_data["msg"])


As it was mentioned previously, exception objects should be the same in case of
direct and HTTP communications. To make it possible specific check function
should be implemented like:

  .. code-block:: python

    def make_exception(exc):
        """Check a class of exception and convert it to rally-like if needed"""
        if isinstance(exc, RallyException):
            return exc
        return RallyException(str(exc))


Command Line Interface
----------------------

CLI should be extended by specific global argument ``--endpoint-url`` for
using remote mode.

Rally-as-a-Service itself should be started via new command:

  .. code-block:: console

    $ rally service start

Rally Web Portal
----------------

Web Portal for Rally can be a good addition. It's implementation can be done
on the top of Rally-as-a-Service which should handle all HTTP stuff.

Since read-only mode of RaaS will be enable from first stages, Web Portal
can be started from providing tables with results of Tasks, Verifications. That
tables should be able to filter results by different fields (tags, time,
deployment, etc.) and make regular or trends reports for selected results.


Alternatives
------------

n/a

Implementation
==============

Assignee(s)
-----------

Primary assignee(s):

  Andrey Kurilin <andr.kurilin@gmail.com>
  Hai Shi <shihai1992@gmail.com>


Work Items
----------

* Make return data of Verify/Verification API serializable
* Make return data of Task API serializable
* Make return data of Deployment API serializable
* Implement the base class for API groups and port Deployment, Task, Verify,
  Verification APIs on it
* Refactor exceptions
* Implement `api_wrapper` decorator and wrap all methods of each API groups
* Implement base logic for as-a-Service
* Extend CLI
* Add simple pages for Web Portal

Dependencies
============

n/a
