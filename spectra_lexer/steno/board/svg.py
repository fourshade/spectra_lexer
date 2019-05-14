from typing import Iterable, List


class SVGElement(dict):
    """ Generic SVG element, meant to be subclassed. """

    TAG: str = "UNDEFINED"

    def transform(self, scale_x:float=1.0, scale_y:float=1.0, dx:float=0.0, dy:float=0.0) -> None:
        """ If only translation is involved, add the simpler translate attribute. """
        if scale_x == 1.0 and scale_y == 1.0:
            tf_string = f"translate({dx}, {dy})"
        else:
            tf_string = f"matrix({scale_x}, 0, 0, {scale_y}, {dx}, {dy})"
        # If a transform already exists, just add it to the end of the string after a space to compose it.
        old_tf = self.get("transform")
        if old_tf is not None:
            tf_string = f"{old_tf} {tf_string}"
        self["transform"] = tf_string

    def serialize(self, write):
        write(f'<{self.TAG}')
        for k in self:
            text = self[k]
            if type(text) is str:
                write(f' {k}="{text}"')
        self._write_ending(write)

    def _write_ending(self, write):
        write('/>\n')


class SVGGroup(SVGElement):
    """ List methods are added; these operate on child elements. """

    TAG = "g"

    _children: List[SVGElement]

    def __init__(self, elems:Iterable[SVGElement]=(), **attrib):
        super().__init__(**attrib)
        self._children = list(elems)

    def append(self, child):
        self._children.append(child)

    def extend(self, child):
        self._children.extend(child)

    def merged(self):
        """ Merge redundant children if possible and return a valid composition. """
        children = self._children
        if len(children) != 1:
            return self
        # A group with only one child does not need to exist. Merge attributes and return only the child.
        child, = children
        child.update(self, **child)
        return child

    def _write_ending(self, write):
        write('>\n')
        for child in self._children:
            child.serialize(write)
        write(f'</{self.TAG}>\n')


class SVGDocument(SVGGroup):
    """ Top-level SVG document. """

    TAG = "svg"

    def encode(self, encoding:str='utf-8') -> bytes:
        """ Add all required fields and encode the entire document into an XML byte string.
            The stdlib uses an I/O stream for this, but append+join on a list is actually faster. """
        stream = []
        write = stream.append
        write(f"<?xml version='1.0' encoding='{encoding}'?>\n")
        self.update(version="1.1", xmlns="http://www.w3.org/2000/svg")
        self.serialize(write)
        return "".join(stream).encode(encoding)


class SVGPath(SVGElement):

    TAG = "path"
