from xml.parsers.expat import ParserCreate

from . import Codec


class XMLCodec(Codec, formats=[".svg", ".xml"]):
    """ Codec to parse a raw XML string into an ID-oriented element dict. """

    def decode(self, contents:str) -> dict:
        """ Return a dict of attributes for each element with a unique ID along with the raw XML string. """
        id_dict = {}
        def start_element(name, attrs):
            if "id" in attrs:
                attrs["name"] = name
                id_dict[attrs["id"]] = attrs
        p = ParserCreate()
        p.StartElementHandler = start_element
        p.Parse(contents)
        return {"raw": contents, "ids": id_dict}

    def encode(self, d:dict) -> str:
        """ We originally saved the string contents under 'raw', so just return that. """
        return d["raw"]
