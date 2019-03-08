from typing import Dict
from xml.parsers.expat import ParserCreate


class SVGParser:

    def parse(self, xml_dict:dict) -> Dict[str, dict]:
        """ Parse element ID names out of the raw XML string data and return the unique set. """
        id_dict = {}
        def start_element(name, attrs):
            if "id" in attrs:
                attrs["name"] = name
                id_dict[attrs["id"]] = attrs
        p = ParserCreate()
        p.StartElementHandler = start_element
        p.Parse(xml_dict["raw"])
        return id_dict
