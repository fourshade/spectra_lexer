from xml.parsers.expat import ParserCreate

from .base import FileHandler


class XML(FileHandler, formats=[".xml"]):
    """ Codec to parse a raw XML string into a dict of elements by specific attributes. """

    @classmethod
    def decode(cls, contents:str, filter_by:str="", **kwargs) -> dict:
        """ Return a dict of attributes for a specifically filtered element along with the raw XML byte string. """
        d = {"raw": contents.encode('utf-8')}
        if not filter_by:
            return d
        d[filter_by] = filter_dict = {}
        def start_element(name:str, attrs:dict) -> None:
            if filter_by in attrs:
                attrs["name"] = name
                filter_dict[attrs[filter_by]] = attrs
        p = ParserCreate(**kwargs)
        p.StartElementHandler = start_element
        p.Parse(contents)
        return d

    @classmethod
    def encode(cls, d:dict, **kwargs) -> str:
        """ We originally saved the string as bytes under 'raw', so just decode and return that. """
        return d["raw"].decode('utf-8')


class SVG(XML, formats=[".svg"]):
    """ Codec to parse an SVG XML string into an ID-oriented element dict. """

    @classmethod
    def decode(cls, contents:str, **kwargs) -> dict:
        """ Return a dict of attributes for each element with a unique ID along with the raw XML string. """
        return super().decode(contents, filter_by="id", **kwargs)
