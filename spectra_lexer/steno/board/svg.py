from typing import Iterable, Iterator, List


class SVGElement:
    """ Abstract SVG element, meant to be subclassed. """

    _tag: str      # Tag name enclosed in <> at element start (and end, if children are included).
    _attrib: dict  # Dict of XML attributes.

    def encode(self, encoding:str='utf-8') -> bytes:
        """ Add the version and XML namespace attribute and encode this element into an XML byte string.
            The stdlib uses an I/O stream for this, but adding strings to a list and joining them is faster. """
        s_list = ['<?xml version="1.0" encoding="', encoding, '"?>\n']
        self.serialize(s_list)
        return "".join(s_list).encode(encoding)

    def serialize(self, s_list:List[str]) -> None:
        """ Recursively write strings representing this object to a list (which will be joined at the end).
            Use += when possible to avoid method call overhead. This is even faster than using f-strings. """
        s_list += '<', self._tag
        for k, v in self._attrib.items():
            s_list += ' ', k, '="', v, '"'
        s_list += '/>',

    def transform(self, scale_x:float, shear_y:float, shear_x:float, scale_y:float, dx:float, dy:float) -> None:
        """ A linear transform with scaling, rotation, translation, etc. can be done in one step with a matrix. """
        self._compose_transform(f'matrix({scale_x}, {shear_y}, {shear_x}, {scale_y}, {dx}, {dy})')

    # If only one type of transformation is involved, use the simpler attributes.
    def rotate(self, degrees:float) -> None:
        self._compose_transform(f'rotate({degrees})')

    def scale(self, scale_x:float, scale_y:float) -> None:
        self._compose_transform(f'scale({scale_x}, {scale_y})')

    def translate(self, dx:float, dy:float) -> None:
        if dx or dy:
            self._compose_transform(f'translate({dx}, {dy})')

    def _compose_transform(self, tf_string:str) -> None:
        """ If a transform already exists, just add it to the end of the string after a space to compose it. """
        if "transform" in self._attrib:
            tf_string = f'{self._attrib["transform"]} {tf_string}'
        self._attrib["transform"] = tf_string


class SVGPath(SVGElement):

    _tag = "path"

    def __init__(self, path_data:str, **attrib:str) -> None:
        """ A path element may not have children, but it must have a path data string. """
        attrib["d"] = path_data
        self._attrib = attrib


class SVGUse(SVGElement):

    _tag = "use"

    def __init__(self, elem_id:str, **attrib:str):
        """ A use element may not have children, but it must have a reference id. """
        attrib["href"] = f"#{elem_id}"
        self._attrib = attrib


class SVGGroup(SVGElement):
    """ Generic SVG group element. Certain methods must be overridden to provide child access. """

    _tag = "g"

    def __init__(self, *elems:SVGElement, **attrib:str) -> None:
        """ Positional args are children, keyword args are attributes. """
        self._children = [*elems]  # List of all child nodes in order.
        self._attrib = attrib

    def append(self, child:SVGElement) -> None:
        self._children.append(child)

    def extend(self, children:Iterable[SVGElement]) -> None:
        self._children += children

    def __iter__(self) -> Iterator[SVGElement]:
        return iter(self._children)

    def __len__(self) -> int:
        return len(self._children)

    def serialize(self, s_list:List[str]) -> None:
        super().serialize(s_list)
        children = self._children
        if children:
            s_list[-1] = '>'
            for child in children:
                child.serialize(s_list)
            s_list += '</', self._tag, '>'


class SVGDefs(SVGGroup):
    """ SVG defs element, meant to hold elements which are reusable.
        Any document that <use>s anything from this element must include it, otherwise references will break. """

    _tag = "defs"


class SVGDocument(SVGGroup):
    """ Top-level SVG document. """

    _tag = "svg"

    def __init__(self, *elems:SVGElement, **attrib:str) -> None:
        attrib.update(version="1.1", xmlns="http://www.w3.org/2000/svg")
        super().__init__(*elems, **attrib)

    def set_viewbox(self, *coords:float) -> None:
        """ Set the (x, y, w, h) sequence of coordinates for the viewbox. """
        self._attrib["viewBox"] = " ".join(map(str, coords))
