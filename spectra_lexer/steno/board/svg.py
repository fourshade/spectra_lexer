from typing import Iterable, Iterator, List


class SVGElement(dict):
    """ Generic SVG element, meant to be subclassed. Default behavior is a simple group of other elements.
        The optimal structure is a dict of XML attributes with certain methods overridden to provide child access. """

    _tag = "g"  # Tag name enclosed in <> at element start (and end, if children are included).

    def __init__(self, *elems, **attrib:str) -> None:
        """ Positional args are children, keyword args are attributes. """
        super().__init__(attrib)
        self._children = [*elems]  # List of all child nodes in order.

    # append, extend, iter, and len methods work on the child list. All others work on the attributes as a dict.
    def append(self, child) -> None:
        self._children.append(child)

    def extend(self, children:Iterable) -> None:
        self._children += children

    def __iter__(self) -> Iterator:
        return iter(self._children)

    def __len__(self) -> int:
        return len(self._children)

    def serialize(self, s_list:List[str]) -> None:
        """ Recursively write strings representing this object to a list (which will be joined at the end).
            Use += when possible to avoid method call overhead. This is even faster than using f-strings. """
        tag = self._tag
        children = self._children
        s_list += '<', tag
        for k, v in self.items():
            s_list += ' ', k, '="', v, '"'
        if children:
            s_list += '>',
            for child in children:
                child.serialize(s_list)
            s_list += '</', tag, '>'
        else:
            s_list += '/>',

    def transform(self, scale_x:float, shear_y:float, shear_x:float, scale_y:float, dx:float, dy:float) -> None:
        """ A linear transform with scaling, rotation, translation, etc. can be done in one step with a matrix. """
        self._compose_transform(f'matrix({scale_x}, {shear_y}, {shear_x}, {scale_y}, {dx}, {dy})')

    # If only one type of transformation is involved, use the simpler attributes.
    def rotate(self, rot:float) -> None:
        self._compose_transform(f'rotate({rot})')

    def scale(self, scale_x:float, scale_y:float) -> None:
        self._compose_transform(f'scale({scale_x}, {scale_y})')

    def translate(self, dx:float, dy:float) -> None:
        if dx or dy:
            self._compose_transform(f'translate({dx}, {dy})')

    def _compose_transform(self, tf_string:str) -> None:
        """ If a transform already exists, just add it to the end of the string after a space to compose it. """
        if "transform" in self:
            tf_string = f'{self["transform"]} {tf_string}'
        self["transform"] = tf_string


class SVGPath(SVGElement):

    _tag = "path"


class SVGUse(SVGElement):

    _tag = "use"


class SVGDefs(SVGElement):
    """ SVG defs element, meant to hold elements which are reusable.
        Any document that <use>s anything from this element must include it, otherwise references will break. """

    _tag = "defs"

    def make_usable(self, elem:SVGElement) -> SVGUse:
        """ Add an element for reuse by ID and return a reference <use> element. Make up an ID if there isn't one. """
        elem_id = elem.setdefault("id", str(id(elem)))
        self.append(elem)
        return SVGUse(href=f"#{elem_id}")


class SVGDocument(SVGElement):
    """ Top-level SVG document. """

    _tag = "svg"

    def set_viewbox(self, *coords:float) -> None:
        """ Set the (x, y, w, h) sequence of coordinates for the viewbox. """
        self["viewBox"] = " ".join(map(str, coords))

    def encode(self, encoding:str='utf-8') -> bytes:
        """ Add the version and XML namespace attribute and encode this entire document into an XML byte string.
            The stdlib uses an I/O stream for this, but adding strings to a list and joining them is faster. """
        s_list = ['<?xml version="1.0" encoding="', encoding, '"?>\n']
        self.update(version="1.1", xmlns="http://www.w3.org/2000/svg")
        self.serialize(s_list)
        return "".join(s_list).encode(encoding)
