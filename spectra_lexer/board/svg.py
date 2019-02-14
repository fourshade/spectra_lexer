from xml.parsers.expat import ParserCreate

from spectra_lexer.resource import ResourceManager

# Resource identifier for the main SVG graphic (containing every element needed).
_BOARD_ASSET_NAME: str = ':/board.svg'


class SVGManager(ResourceManager):
    """ SVG board diagram parser for the Spectra program. Saving is not allowed. """

    files = [_BOARD_ASSET_NAME]

    def parse(self, xml_dict:dict) -> dict:
        """ Parse element ID names out of the raw XML string data. """
        d = {}
        def start_element(name, attrs):
            if "id" in attrs:
                attrs["name"] = name
                d[attrs["id"]] = attrs
        p = ParserCreate()
        p.StartElementHandler = start_element
        p.Parse(xml_dict["raw"])
        xml_dict["ids"] = d
        return xml_dict

    def save(self, filename:str, obj:object) -> tuple:
        """ Board graphics data may not be saved back to disk. """
        raise TypeError("Cannot save board SVG data to disk.")
