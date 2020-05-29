from typing import List, Sequence


class XMLElement:
    """ Simple XML element with no character data or namespace support. """

    def __init__(self, tag:str, *children:"XMLElement", **attrib:str) -> None:
        """ Positional args are children, keyword args are attributes. """
        self._tag = tag            # Tag name enclosed in <> at element start (and end, if children are included).
        self._children = children  # All child elements in order.
        self._attrib = attrib      # Dict of XML attributes.

    def encode(self, encoding='utf-8') -> bytes:
        """ Encode this element into an XML byte string starting with the standard XML header. """
        s = f'<?xml version="1.0" encoding="{encoding}"?>\n{self.serialize()}'
        return s.encode(encoding)

    def serialize(self) -> str:
        """ Serialize this element and its children recursively into a string.
            The stdlib uses an I/O stream for this, but adding strings to a list and joining them is faster. """
        s_list = []
        self._serialize(s_list)
        return "".join(s_list)

    def _serialize(self, s_list:List[str]) -> None:
        """ Recursively write strings representing this object to a list (which will be joined at the end).
            Use += when possible to avoid method call overhead. This is even faster than using f-strings. """
        s_list += '<', self._tag
        for k, v in self._attrib.items():
            s_list += ' ', k, '="', v, '"'
        children = self._children
        if children:
            s_list += '>',
            for child in children:
                child._serialize(s_list)
            s_list += '</', self._tag, '>'
        else:
            s_list += '/>',


class SVGElementFactory:
    """ Factory for XML elements formatted as necessary for SVG. """

    def __init__(self, elem_cls=XMLElement) -> None:
        self._elem_cls = elem_cls

    def path(self, path_data:str, transform:str=None, **style:str) -> XMLElement:
        """ A path element may not have children, but it must have a path data string. """
        attrib = {"d": path_data}
        if style:
            style_attrs = []
            for k, v in style.items():
                style_attrs += k, ":", v, ";"
            attrib["style"] = "".join(style_attrs).replace("_", "-")
        if transform is not None:
            attrib["transform"] = transform
        return self._elem_cls("path", **attrib)

    def group(self, *children:XMLElement, **attrib:str) -> XMLElement:
        """ Generic SVG group element. """
        return self._elem_cls("g", *children, **attrib)

    def defs(self, *children:XMLElement) -> XMLElement:
        """ SVG defs element, meant to hold child elements which are reusable.
            Any document that <use>s anything from this element must include it, otherwise references will break. """
        return self._elem_cls("defs", *children)

    def use(self, elem_id:str) -> XMLElement:
        """ A use element may not have children, but it must have a reference id. """
        return self._elem_cls("use", href=f"#{elem_id}")

    def svg(self, *children:XMLElement, viewbox:Sequence[int]=(0, 0, 100, 100)) -> XMLElement:
        """ Top-level SVG document. Set the (x, y, w, h) sequence of coordinates as the viewbox. """
        x, y, w, h = viewbox
        return self._elem_cls("svg", *children,
                              version="1.1", xmlns="http://www.w3.org/2000/svg",
                              viewBox=f"{x} {y} {w} {h}")
