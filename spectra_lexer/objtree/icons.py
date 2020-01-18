import csv
from typing import Iterable, Optional

SVGIconData = bytes  # Marker class for SVG icon data structure (formatted XML bytes data).


class SVGIconFinder:

    COMPONENT_ICON_ID = "__COMPONENT__"  # ID of special icon for application components.
    METATYPE_ICON_ID = "__METATYPE__"    # ID of special icon for metaclasses.

    def __init__(self, cmp_package:str=None) -> None:
        self._cmp_package = cmp_package  # Optional name of Python package for components using the gear icon.
        self._icon_dict = {}             # Dict of SVG XML icon data keyed by the names of object data types.

    def load_csv(self, data:bytes, encoding='utf-8') -> None:
        """ Parse CSV formatted icon data. The first row contains only one field:
            the basic document structure with header and footer, usable as a format string.
            In all other rows, the last field is the SVG icon data itself, and every other field
            contains the name of a data type alias that uses the icon described by that data. """
        lines = data.decode(encoding).splitlines()
        [fmt], *items = csv.reader(map(str.strip, lines))
        # Format each icon from the packaged bytes data and add them to the dict under each alias.
        for *aliases, xml_data in items:
            xml = fmt.format(xml_data).encode(encoding)
            for n in aliases:
                self._icon_dict[n] = xml

    def get_best(self, choices:Iterable[str], *, module_name="", is_metacls=False) -> Optional[SVGIconData]:
        """ Return the best available icon out of <choices> from most wanted to least, with special exceptions. """
        choice_list = []
        # Metaclasses show a "type of types" icon if available.
        if is_metacls:
            choice_list.append(self.METATYPE_ICON_ID)
        choice_list += choices
        # Objects originating from the 'component' package show a gear icon if no other choice applies.
        if self._cmp_package is not None and module_name.startswith(self._cmp_package):
            choice_list.pop()
            choice_list.append(self.COMPONENT_ICON_ID)
        return self._get_best(choice_list)

    def _get_best(self, choices:Iterable[str]) -> Optional[SVGIconData]:
        """ Return the best available icon out of <choices> from most wanted to least. """
        for choice in choices:
            if choice in self._icon_dict:
                return self._icon_dict[choice]
        return None
