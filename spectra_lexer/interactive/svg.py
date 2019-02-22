from xml.parsers.expat import ParserCreate

from spectra_lexer.resource import ResourceManager

# Resource identifier for the main SVG graphic. Contains every element needed.
_BOARD_ASSET_NAME = ':/board.svg'


class SVGManager(ResourceManager):
    """ SVG board diagram parser for the Spectra program. Saving is not allowed. """

    ROLE = "svg"
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
