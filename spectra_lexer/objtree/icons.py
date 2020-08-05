from typing import Iterator, Optional

SVGIconData = str  # Marker for SVG icon data type.


class SVGIconFinder:

    METATYPE_ID = "__METATYPE__"    # ID of special icon for metaclasses.
    COMPONENT_ID = "__COMPONENT__"  # ID of special icon for application components.

    def __init__(self, cmp_package:str=None) -> None:
        self._cmp_package = cmp_package  # Optional name of Python package for components using the gear icon.
        self._icon_dict = {}             # Dict of SVG XML icon data keyed by the names of object data types.

    def load(self, filename:str, encoding='utf-8') -> None:
        """ Parse an icon data file. The first and last items define the template. For other items,
            the first row contains the names of data types that use the icon XML in the following rows. """
        with open(filename, encoding=encoding) as fp:
            s = ''.join(fp)
        header, *items, footer = s.split('\n\n')
        for item in items:
            types, xml = item.split('\n', 1)
            icon = header + xml + footer
            for name in types.split(','):
                self._icon_dict[name] = icon

    def _find_ids(self, obj:object) -> Iterator[str]:
        """ Yield icon ID choices for <obj> from most wanted to least. """
        # Metaclasses show a "type of types" icon if available.
        if isinstance(obj, type) and issubclass(obj, type):
            yield self.METATYPE_ID
        # Most objects show the most specific type-based icon they can.
        tp = type(obj)
        for cls in tp.__mro__[:-1]:
            yield cls.__name__
        # Objects originating from the 'component' package show a gear icon if no other icon applies.
        if self._cmp_package is not None and tp.__module__.startswith(self._cmp_package):
            yield self.COMPONENT_ID
        # Only use a generic object icon if all other matches fail.
        yield object.__name__

    def get_best(self, obj:object) -> Optional[SVGIconData]:
        """ Return the most specific available icon for <obj>. """
        for icon_id in self._find_ids(obj):
            if icon_id in self._icon_dict:
                return self._icon_dict[icon_id]
        return None
