from typing import Iterable, Optional

SVGIconData = bytes  # Marker class for SVG icon data structure (formatted XML bytes data).


class SVGIconFinder:

    COMPONENT_ID = "__COMPONENT__"  # ID of special icon for application components.
    METATYPE_ID = "__METATYPE__"    # ID of special icon for metaclasses.

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

    def _get_best(self, choices:Iterable[str]) -> Optional[SVGIconData]:
        """ Return the best available icon out of <choices> from most wanted to least. """
        for choice in choices:
            if choice in self._icon_dict:
                return self._icon_dict[choice]
        return None

    def get_best(self, choices:Iterable[str], *, module_name="", is_metacls=False) -> Optional[SVGIconData]:
        """ Return the best available icon out of <choices> from most wanted to least, with special exceptions. """
        choice_list = []
        # Metaclasses show a "type of types" icon if available.
        if is_metacls:
            choice_list.append(self.METATYPE_ID)
        choice_list += choices
        # Objects originating from the 'component' package show a gear icon if no other choice applies.
        if self._cmp_package is not None and module_name.startswith(self._cmp_package):
            choice_list[-1] = self.COMPONENT_ID
        return self._get_best(choice_list)
