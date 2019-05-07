""" Module for container classes that access items held on a specific attribute. """

import builtins
import types

from .collection import use_if_object_has_attr
from .container import Container, MutableKeyContainer
from spectra_lexer.types import delegate_to


@use_if_object_has_attr("__class__")
class ClassContainer(Container):

    color = (32, 32, 128)  # Class containers are blue.
    key_tooltip = value_tooltip = "Auto-generated item; cannot edit."
    _EXCLUDED_CLASSES: set = {i for m in (builtins, types) for i in vars(m).values() if isinstance(i, type)}

    _cls_tree: dict = {}  # Pre-computed class hierarchy tree by name.

    def __init__(self, obj):
        """ Allow class access if the object has an instance dict, or metaclass access if the object *is* a class.
            The main exception is type, which is its own class and would expand indefinitely.
            Others include built-in types which provide next to nothing useful in their attr listings. """
        super().__init__(obj)
        if hasattr(obj, "__dict__"):
            self._cls_tree = {cls.__name__: cls for cls in type(obj).__mro__ if cls not in self._EXCLUDED_CLASSES}

    __len__ = delegate_to("_cls_tree")
    __iter__ = delegate_to("_cls_tree")
    __getitem__ = delegate_to("_cls_tree")


@use_if_object_has_attr("__slots__")
class AttrContainer(Container):

    _ATTR = "__slots__"

    # Slots are tricky to modify. Keep them as read-only for now.
    key_tooltip = value_tooltip = "Attributes are slots; cannot edit."

    def __init__(self, obj):
        """ The chosen attribute container object is saved for easy access. """
        super().__init__(obj)
        self._attro = getattr(self._obj, self._ATTR)

    __len__ = delegate_to("_attro")
    __iter__ = delegate_to("_attro")

    def __getitem__(self, key:str):
        """ Return the attribute under <key> by any method we can. """
        try:
            return getattr(self._obj, key)
        except (AttributeError, TypeError):
            return self._attro[key]


@use_if_object_has_attr("__dict__")
class DictAttrContainer(AttrContainer, MutableKeyContainer):

    _ATTR = "__dict__"

    key_tooltip: str = "Double-click to change this attribute name."
    value_tooltip: str = "Double-click to edit this attribute value."

    def __delitem__(self, key:str) -> None:
        """ Delete the attribute under <key> if it exists. """
        if hasattr(self._obj, key):
            delattr(self._obj, key)

    def __setitem__(self, key:str, value) -> None:
        """ __dict__ may be a mappingproxy, so setattr is the best way to set attributes.
            Deleting the attribute before setting the new value may help to override data descriptors. """
        del self[key]
        setattr(self._obj, key, value)
