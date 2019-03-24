from xml.parsers.expat import ParserCreate

from .base import FileHandler


class XML(FileHandler, formats=[".svg", ".xml"]):
    """ Codec to parse a raw XML string into an ID-oriented element dict. """

    @classmethod
    def decode(cls, contents:str) -> dict:
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

    @classmethod
    def encode(cls, d:dict) -> str:
        """ We originally saved the string contents under 'raw', so just return that. """
        return d["raw"]
