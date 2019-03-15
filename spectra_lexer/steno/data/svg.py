from typing import Dict
from xml.parsers.expat import ParserCreate

from spectra_lexer import Component


class SVGManager(Component):
    """ SVG parser for the Spectra program. Used for the steno board diagram. """

    file = Option("cmdline", "svg-file", ":/board.svg", "SVG file with graphics for the steno board diagram.")

    @pipe("start", "new_svg")
    @pipe("svg_load", "new_svg")
    def load(self, filename:str="") -> Dict[str, dict]:
        """ Load an SVG file and parse element ID names out of the raw XML string data. """
        xml_dict = self.engine_call("file_load", filename or self.file)
        xml_dict["ids"] = self._parse(xml_dict["raw"])
        return xml_dict

    def _parse(self, raw_data:str) -> Dict[str, dict]:
        """ Parse element ID names out of the raw XML string data and return the unique set. """
        id_dict = {}
        def start_element(name, attrs):
            if "id" in attrs:
                attrs["name"] = name
                id_dict[attrs["id"]] = attrs
        p = ParserCreate()
        p.StartElementHandler = start_element
        p.Parse(raw_data)
        return id_dict
