from xml.parsers.expat import ParserCreate

from spectra_lexer.dict import ResourceManager

# Resource identifier for the main SVG graphic (containing every element needed).
_BOARD_ASSET_NAME: str = ':/board.svg'


class BoardManager(ResourceManager):
    """ SVG board diagram parser for the Spectra program. Saving is not allowed. """

    ROLE = "dict_board"
    files = [_BOARD_ASSET_NAME]

    def parse(self, d:dict) -> dict:
        """ Parse element ID names out of the raw XML string data. """
        p = ParserCreate()
        def start_element(name, attrs):
            if name == "g" and "id" in attrs:
                d[attrs["id"]] = attrs
        p.StartElementHandler = start_element
        p.Parse(d["raw"])
        return d

    def save(self, filename:str, obj:object) -> tuple:
        """ Board graphics data may not be saved back to disk. """
        raise TypeError("Cannot save board SVG data to disk.")
