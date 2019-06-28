from spectra_lexer.types.codec import XMLElement


class SVGElement(XMLElement):
    """ Generic SVG element, meant to be subclassed. """

    tag = "g"  # Default behavior is a simple group of other elements.

    def transform(self, scale_x:float=1.0, scale_y:float=1.0, dx:float=0.0, dy:float=0.0) -> None:
        """ A transform with scaling and translation is done in one step with a matrix. """
        self._compose_transform(f'matrix({scale_x}, 0, 0, {scale_y}, {dx}, {dy})')

    def translate(self, dx:float=0.0, dy:float=0.0) -> None:
        """ If only translation is involved, use the simpler translate attribute. """
        if dx or dy:
            self._compose_transform(f'translate({dx}, {dy})')

    def _compose_transform(self, tf_string:str) -> None:
        """ If a transform already exists, just add it to the end of the string after a space to compose it. """
        if "transform" in self:
            tf_string = f'{self["transform"]} {tf_string}'
        self["transform"] = tf_string


class SVGPath(SVGElement):

    tag = "path"


class SVGUse(SVGElement):

    tag = "use"


class SVGDefs(SVGElement):
    """ SVG defs element, meant to hold elements which are reusable.
        Any document that <use>s anything from this element must include it, otherwise references will break. """

    tag = "defs"

    def make_usable(self, child:SVGElement) -> SVGUse:
        """ Add a reusable child element by ID and return a reference <use> element. """
        try:
            child_id = child["id"]
        except KeyError as e:
            raise ValueError("Only elements with an ID are usable from a <defs> element.") from e
        self.append(child)
        return SVGUse(href=f"#{child_id}")


class SVGDocument(SVGElement):
    """ Top-level SVG document. """

    tag = "svg"

    def __init__(self, *elems, **attrib):
        attrib.update(version="1.1", xmlns="http://www.w3.org/2000/svg")
        super().__init__(*elems, **attrib)

    def set_viewbox(self, *coords:float) -> None:
        """ Set the (x, y, w, h) sequence of coordinates for the viewbox. """
        self["viewBox"] = " ".join(map(str, coords))
