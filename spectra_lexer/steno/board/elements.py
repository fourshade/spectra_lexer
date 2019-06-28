from collections import defaultdict
from xml.etree.ElementTree import Element

from .svg import SVGGroup, SVGPath


class SVGGroupEx(SVGGroup):
    """ SVG group element with metadata for additional processing. """

    text_attrs: dict = {}  # Holds text drawing attributes from the last shape.
    offset: complex = 0j   # Holds the total offset for use in annotations (such as inversion arrows).

    def add_offset(self, dx:float, dy:float) -> None:
        """ Offsets are stored and added as complex numbers, which work well for 2D points. """
        self.offset += complex(dx, dy)


class SVGElementParser(dict):

    OFFSET_ATTR: str = "keyoffset"  # Holds the total offset for use in annotations (such as inversion arrows).

    def __init__(self, defs:dict):
        """ Instantiate all required attribute processors from nested classes. """
        proc_classes = [(k[4:].lower(), getattr(self, k)) for k in dir(self) if k.startswith("Proc")]
        super().__init__({k: cls(defs.get(k) or {}) for k, cls in proc_classes})

    def __call__(self, elem:Element, attrib=None) -> SVGGroupEx:
        """ Parse XML node attributes and children into a usable SVG group element, adding anything that
            attributes direct us to. Add children to subgroups and merge any redundant elements at the end. """
        if attrib is None:
            attrib = dict(elem.items())
        group = SVGGroupEx(map(self, elem), **attrib)
        self._run_procs(group)
        return group.merged()

    def _run_procs(self, elem:SVGGroupEx) -> None:
        """ Pop all processable attrs into a list before starting on any of them. """
        proc_attrs = [(f, elem.pop(k)) for k, f in self.items() if k in elem]
        for f, v in proc_attrs:
            f(elem, v)

    class ProcPos(dict):

        def __call__(self, elem:SVGGroupEx, id:str) -> None:
            dx, dy = self[id]
            elem.add_offset(dx, dy)
            elem.transform(1.0, 1.0, dx, dy)

    class ProcShape(dict):

        def __call__(self, elem:SVGGroupEx, ids:str) -> None:
            for id in ids.split():
                shape = self[id].copy()
                path = shape.pop("d")
                elem.text_attrs = shape
                elem.append(SVGPath(d=path))

    class ProcText(dict):

        CENTER: str = "txtcenter"
        MAXWIDTH: str = "txtwidth"
        SPACING: str = "txtspacing"
        BASE_FONT_SIZE: float = 24 / 1000  # Size is 24 pt, and text paths are defined with an em box of 1000 units.

        def __call__(self, elem:SVGGroupEx, text:str) -> None:
            """ SVG fonts are not supported on any major browsers, so we must draw them as paths. """
            n = len(text)
            if n:
                attrs = elem.text_attrs
                cx, cy = attrs[self.CENTER]
                elem.add_offset(cx, cy)
                spacing = attrs[self.SPACING]
                scale = min(1.0, attrs[self.MAXWIDTH] / (n * spacing))
                spacing *= scale
                x = cx - ((spacing / 2) * n)
                y = cy + (10 * scale) - 3
                font_scale_x = scale * self.BASE_FONT_SIZE
                font_scale_y = -font_scale_x
                for k in text:
                    char = SVGPath(fill="#000000", d=self[k])
                    char.transform(font_scale_x, font_scale_y, x, y)
                    elem.append(char)
                    x += spacing


class XMLElementDict(defaultdict):
    """ A dict of XML elements by tag name. """

    _procs: SVGElementParser

    def __init__(self, defs:dict):
        """ Instantiate all required attribute processors from the module body. """
        super().__init__(dict)
        self._proc = SVGElementParser(defs)

    def add_recursive(self, elem:Element, **attrib) -> None:
        """ Search for and process elements with IDs recursively. Make each child inherit from its predecessor. """
        attrib.update(elem.items())
        e_id = attrib.get("id")
        if e_id is not None:
            self[elem.tag][e_id] = self._proc(elem, attrib)
        else:
            for child in elem:
                self.add_recursive(child, **attrib)
