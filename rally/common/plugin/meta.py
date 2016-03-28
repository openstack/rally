# Copyright 2015: Mirantis Inc.
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


class MetaMixin(object):
    """Safe way to store meta information related to class object.

    We are storing information in class object instead of the instance.
    Information is stored in dict that is initialized only once during the
    load of module, it means that all subclasses of this class will point to
    the same dict object with the information.

    Sample that explains why it's important to use MetaMixin:

        >>> # Using direct fields
        >>>
        >>> class A(object):
        >>>     _meta = {}
        >>>
        >>> class B(A):
        >>>    pass
        >>>
        >>> B._meta["a"] = 10
        >>> assert A._meta["a"] == 10  # We changed meta of base class, which
                                       # is going to produce nasty bugs

        >>> # MetaMixin in action
        >>>
        >>> class A(MetaMixin):
        >>>    pass
        >>>
        >>> class B(A):
        >>>    pass
        >>>
        >>> A._meta_set("a", 10)   # Raises ReferenceError
        >>> A._meta_init()
        >>> A._meta_set("a", 10)   # Set meta field "a"
        >>>
        >>> B._meta_get("a")       # Raises ReferenceError
        >>> B._meta_init()
        >>> B._meta_set("a", 20)   # Set meta field "a"
        >>>
        >>> assert A._meta_get("a")  == 10
        >>> assert B._meta_get("a")  == 20
    """

    @classmethod
    def _meta_init(cls):
        """Initialize meta for this class."""
        cls._meta = {}

    @classmethod
    def _meta_clear(cls):
        cls._meta.clear()    # NOTE(boris-42): make sure that meta is deleted
        delattr(cls, "_meta")

    @classmethod
    def _meta_is_inited(cls, raise_exc=True):
        """Check if meta is initialized.

        It means that this class has own cls._meta object (not pointer
        to parent cls._meta)

        To do this we should check 2 things:
        1) cls has attribute _meta
        2) cls._meta is not pointer to parent._meta

        """
        if (not hasattr(cls, "_meta")
           or cls._meta is getattr(super(cls, cls), "_meta", None)):
            if raise_exc:
                raise ReferenceError(
                    "Trying to use MetaMixin before initialization %s. "
                    "Call _meta_init() before using it" % cls)
            return False
        return True

    @classmethod
    def _meta_get(cls, key, default=None):
        """Get value corresponding to key in meta data."""
        cls._meta_is_inited()
        return cls._meta.get(key, default)

    @classmethod
    def _meta_set(cls, key, value):
        """Set value for key in meta."""
        cls._meta_is_inited()
        cls._meta[key] = value

    @classmethod
    def _meta_setdefault(cls, key, value):
        """Set default value for key in meta."""
        cls._meta_is_inited()
        cls._meta.setdefault(key, value)
