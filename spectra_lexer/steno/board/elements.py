from collections import defaultdict
from typing import Callable, Dict
from xml.etree.ElementTree import Element

from .svg import SVGGroup, SVGPath


class XMLElementDict(defaultdict):
    """ A dict of XML elements by tag name. """

    _procs: Dict[str, Callable]

    def __init__(self, defs:dict):
        """ Instantiate all required attribute processors from the module body. """
        super().__init__(dict)
        proc_classes = {k[4:].lower(): cls for k, cls in globals().items() if k.startswith("Proc")}
        self._procs = {k: cls(defs.get(k) or {}) for k, cls in proc_classes.items()}

    def add_recursive(self, elem:Element, **attrib) -> None:
        """ Search for elements with IDs recursively. Make each child inherit from its predecessor. """
        attrib.update(elem.items())
        e_id = attrib.get("id")
        if e_id is not None:
            self[elem.tag][e_id] = self._parse(elem, attrib)
        else:
            for child in elem:
                self.add_recursive(child, **attrib)

    def _parse(self, elem:Element, attrib=None) -> SVGGroup:
        """ Parse XML node attributes and children into a usable SVG group element, adding anything that
            attributes direct us to. Add children to subgroups and merge any redundant elements at the end. """
        if attrib is None:
            attrib = dict(elem.items())
        group = SVGGroup(map(self._parse, elem), **attrib)
        self._run_procs(group)
        return group.merged()

    def _run_procs(self, elem:SVGGroup) -> None:
        """ Pop all processable attrs into a list before starting on any of them. """
        proc_attrs = [(f, elem.pop(k)) for k, f in self._procs.items() if k in elem]
        for f, v in proc_attrs:
            f(elem, v)


class ProcPos(dict):

    OFFSET: str = "keyoffset"

    def __call__(self, elem:SVGGroup, id:str) -> None:
        elem[self.OFFSET] = self[id]
        elem.transform(1.0, 1.0, *self[id])


class ProcShape(dict):

    def __call__(self, elem:SVGGroup, ids:str) -> None:
        for id in ids.split():
            shape = self[id].copy()
            path = shape.pop("d")
            elem.update(shape)
            elem.append(SVGPath(d=path))


class ProcText(dict):

    CENTER: str = "txtcenter"
    MAXWIDTH: str = "txtwidth"
    SPACING: str = "txtspacing"
    BASE_FONT_SIZE: float = 24 / 1000  # Size is 24 pt, and text paths are defined with an em box of 1000 units.

    def __call__(self, elem:SVGGroup, text:str) -> None:
        """ SVG fonts are not supported on any major browsers, so we must draw them as paths. """
        n = len(text)
        if n:
            spacing = elem[self.SPACING]
            scale = min(1.0, elem[self.MAXWIDTH] / (n * spacing))
            spacing *= scale
            cx, cy = elem[self.CENTER]
            x = cx - ((spacing / 2) * n)
            y = cy + (10 * scale) - 3
            font_scale_x = scale * self.BASE_FONT_SIZE
            font_scale_y = -font_scale_x
            for k in text:
                char = SVGPath(fill="#000000", d=self[k])
                char.transform(font_scale_x, font_scale_y, x, y)
                elem.append(char)
                x += spacing
