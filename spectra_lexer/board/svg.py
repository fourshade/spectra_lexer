from typing import Mapping, Sequence

XML_HEADER = '<?xml version="1.0" encoding="utf-8"?>'


class SVGElement:
    """ SVG/XML element that may be serialized into a string. """

    def __str__(self) -> str:
        """ Encode this element into a string. """
        raise NotImplementedError


class SVGStyle:
    """ Container for any valid combination of SVG style attributes (e.g. fill, stroke, stroke-width).
        Due to Python keyword argument rules, attributes with hyphens must be passed using underscores instead. """

    def __init__(self, **attrs:str) -> None:
        self._attrs = attrs

    def to_string(self) -> str:
        sections = []
        for k, v in self._attrs.items():
            sections += [k.replace("_", "-"), ":", v, ";"]
        return "".join(sections)


class SVGElementFactory:
    """ Factory for XML elements formatted as necessary for SVG. """

    @staticmethod
    def _element(tag:str, children:Sequence[SVGElement], attrib:Mapping[str, str]) -> SVGElement:
        """ Create an SVG element. It must be an object that returns valid SVG code on calling __str__.
            The simplest object that can do this is...just a plain string.
            We can just assemble the code into a string here and return that.
            tag      - XML tag name.
            children - Sequence of all child elements in order.
            attrib   - Mapping of all XML attributes. """
        s_list = ['<', tag]
        for k, v in attrib.items():
            s_list += [' ', k, '="', v, '"']
        if children:
            s_list.append('>')
            s_list += map(str, children)
            s_list += ['</', tag, '>']
        else:
            s_list.append('/>')
        return "".join(s_list)

    def path(self, path_data:str, style:SVGStyle=None, **attrib:str) -> SVGElement:
        """ A path element may not have children, but it must have a path data string. """
        attrib["d"] = path_data
        if style is not None:
            attrib["style"] = style.to_string()
        return self._element("path", (), attrib)

    def group(self, *children:SVGElement, **attrib:str) -> SVGElement:
        """ Generic SVG group element. """
        return self._element("g", children, attrib)

    def defs(self, *children:SVGElement) -> SVGElement:
        """ SVG defs element, meant to hold child elements which are reusable.
            Any document that <use>s anything from this element must include it, otherwise references will break. """
        return self._element("defs", children, {})

    def use(self, elem_id:str) -> SVGElement:
        """ A use element may not have children, but it must have a reference id. """
        attrib = {"href": "#" + elem_id}
        return self._element("use", (), attrib)

    def svg(self, *children:SVGElement, viewbox:Sequence[int]=(0, 0, 100, 100)) -> SVGElement:
        """ Top-level SVG document. Set the (x, y, w, h) sequence of coordinates as the viewbox. """
        x, y, w, h = viewbox
        attrib = dict(version="1.1", xmlns="http://www.w3.org/2000/svg", viewBox=f"{x} {y} {w} {h}")
        return self._element("svg", children, attrib)
