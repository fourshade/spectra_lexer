from io import TextIOWrapper
from typing import Iterator, List

from .container import Container, ContainerIndex
from .item import KeyItem, TypeItem, ValueItem


class Row(list):
    """ The most basic type of tree item row, without contents. """

    def __init__(self, obj:object, *data):
        classes = (KeyItem, TypeItem, ValueItem)
        if data:
            items = [cls(d) for cls, d in zip(classes, data)]
        else:
            items = [cls() for cls in classes]
        super().__init__(items)
        for item in self:
            item.set_object(obj)


class ContainerRow(Row):
    """ Handles rows with "containers" that display the contents of an object. """

    def __init__(self, factory, *args):
        """ The collection has child items if any container does.
            If any containers want to display their item count, display it next to the type info label. """
        super().__init__(*args)
        if factory:
            key_item, type_item, _ = self
            key_item["has_children"] = True
            key_item["child_data"] = factory
            item_counts = factory.item_counts()
            if item_counts:
                count = sum(item_counts)
                c_text = f' - {count} item{"s" * (count != 1)}'
                type_item["text"] += c_text


class ExceptionRow(ContainerRow):
    """ Exceptions use custom container classes and are bright red. """

    def __init__(self, *args):
        super().__init__(*args)
        for item in self:
            item["color"] = (192, 0, 0)


class RowFactory:

    # Base data types to treat as atomic/indivisible. Attempting iteration on these is either wasteful or harmful.
    _ATOMIC_TYPES: set = {type(None), type(...),  # System singletons.
                          bool, int, float,       # Guaranteed not iterable.
                          str, bytes, bytearray,  # Items are just characters; do not iterate over these.
                          range, slice,           # Results of iteration are completely pre-determined by constants.
                          TextIOWrapper}          # Iteration may crash the program if std streams are in use.

    _containers: List[Container]

    def __init__(self, obj:object):
        self._containers = ContainerIndex.match_all(obj)

    def __bool__(self):
        """ The factory has child items to make if any container does. """
        return any(self._containers)

    def __iter__(self) -> Iterator[Row]:
        """ Create and yield rows from each container in turn. """
        for c in self._containers:
            try:
                for args in c.contents():
                    yield self.generate(*args)
            except Exception as e:
                # Unpredictable exceptions may arise during introspection, so just present an error for any one.
                yield self.generate(e, {"text": "ERROR"}, {}, {})

    def item_counts(self):
        return [len(c) for c in self._containers if c.show_item_count]

    @classmethod
    def generate(cls, obj:object, *data):
        if type(obj) in cls._ATOMIC_TYPES:
            return Row(obj, *data)
        containers = cls(obj)
        if isinstance(obj, BaseException):
            return ExceptionRow(containers, obj, *data)
        return ContainerRow(containers, obj, *data)
