from typing import Mapping, Sequence, Union

from . import IPathCanvas, ISerializable

# Pre-constructed strings can count as any serializable type.
_SVGElement = ISerializable
_SVGAttribute = ISerializable
_SVGPath = _SVGAttribute
SVGElement = Union[_SVGElement, str]
SVGAttribute = Union[_SVGAttribute, str]
SVGPath = Union[_SVGPath, str]
SVGElements = Sequence[SVGElement]
SVGAttributes = Mapping[str, SVGAttribute]


def _fmt(x:complex) -> str:
    """ Format a complex number as a coordinate pair string. Remove trailing zeros to reduce file size. """
    return f"{x.real:.4g},{x.imag:.4g}"


class SVGPathCanvas(_SVGPath, IPathCanvas):
    """ Compiles SVG path commands into strings. """

    def __init__(self) -> None:
        self._cmds = []

    def move_to(self, p:complex, relative=False) -> None:
        self._cmds += "m" if relative else "M", _fmt(p)

    def line_to(self, ep:complex, relative=False) -> None:
        self._cmds += "l" if relative else "L", _fmt(ep)

    def quad_to(self, cp:complex, ep:complex, relative=False) -> None:
        self._cmds += "q" if relative else "Q", _fmt(cp), _fmt(ep)

    def cubic_to(self, cp:complex, dp:complex, ep:complex, relative=False) -> None:
        self._cmds += "c" if relative else "C", _fmt(cp), _fmt(dp), _fmt(ep)

    def arc_to(self, radii:complex, ep:complex, sweep_cw=False, large_arc=False, relative=False) -> None:
        self._cmds += "a" if relative else "A", _fmt(radii), f"0 {large_arc:d},{sweep_cw:d}", _fmt(ep)

    def close(self) -> None:
        self._cmds += "z",

    def __str__(self) -> str:
        """ Return an SVG path string from the current series of commands. """
        return " ".join(self._cmds)


class SVGStyle(_SVGAttribute):
    """ Container for any valid combination of SVG style attributes (e.g. fill, stroke, stroke-width).
        Due to Python keyword argument rules, attributes with hyphens must be passed using underscores instead. """

    def __init__(self, **attrs:str) -> None:
        self._attrs = attrs

    def __str__(self) -> str:
        sections = []
        for k, v in self._attrs.items():
            sections += [k.replace("_", "-"), ":", v, ";"]
        return "".join(sections)


class SVGTransform(_SVGAttribute):
    """ Container for a valid SVG transform.
        Default is matrix form with coefficients in this order:
        [a, c, e]
        [b, d, f] """

    header = 'matrix'

    def __init__(self, *coefs:float) -> None:
        self._coefs = coefs

    def __str__(self) -> str:
        """ Return the transform in SVG format. Tuple string format is exactly what we need. """
        return self.header + str(self._coefs)


class SVGTranslation(SVGTransform):
    """ Container for an SVG translation.
        There are only two coefficients, x and y. """

    header = 'translate'


SVGViewbox = Sequence[int]  # (x, y, w, h) sequence of coordinates for the visible area of an SVG document.


class SVGElementFactory:
    """ Factory for XML elements formatted as necessary for SVG. """

    @staticmethod
    def _element(tag:str, children:SVGElements, attrib:SVGAttributes) -> SVGElement:
        """ Create an SVG element. It must be an object that returns valid SVG code on calling __str__.
            The simplest object that can do this is...just a plain string.
            We can just assemble the code into a string here and return that.
            tag      - XML tag name.
            children - Sequence of all child elements in order.
            attrib   - Mapping of all XML attributes. """
        s_list = ['<', tag]
        for k, v in attrib.items():
            s_list += [' ', k, '="', str(v), '"']
        if children:
            s_list.append('>')
            s_list += map(str, children)
            s_list += ['</', tag, '>']
        else:
            s_list.append('/>')
        return "".join(s_list)

    def path(self, path:SVGPath, style:SVGStyle=None, tfrm:SVGTransform=None) -> SVGElement:
        """ A path element may not have children, but it must have a path data string. """
        attrib = {"d": path}
        if style is not None:
            attrib["style"] = style
        if tfrm is not None:
            attrib["transform"] = tfrm
        return self._element("path", (), attrib)

    def group(self, children:SVGElements=(), tfrm:SVGTransform=None, elem_id:str=None) -> SVGElement:
        """ Generic SVG group element. """
        attrib = {}
        if tfrm is not None:
            attrib["transform"] = tfrm
        if elem_id is not None:
            attrib["id"] = elem_id
        return self._element("g", children, attrib)

    def defs(self, children:SVGElements=()) -> SVGElement:
        """ SVG defs element, meant to hold child elements which are reusable.
            Any document that <use>s anything from this element must include it, otherwise references will break. """
        return self._element("defs", children, {})

    def use(self, elem_id:str) -> SVGElement:
        """ A use element may not have children, but it must have a reference id. """
        attrib = {"href": "#" + elem_id}
        return self._element("use", (), attrib)

    DEFAULT_ATTRIB = {"version": "1.1",
                      "xmlns": "http://www.w3.org/2000/svg",
                      "viewBox": "0 0 100 100"}

    def svg(self, children:SVGElements=(), viewbox:SVGViewbox=None) -> SVGElement:
        """ Top-level SVG document. """
        attrib = self.DEFAULT_ATTRIB.copy()
        if viewbox is not None:
            assert len(viewbox) == 4
            attrib["viewBox"] = " ".join(map(str, viewbox))
        return self._element("svg", children, attrib)
