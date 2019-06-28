from ast import literal_eval
from configparser import ConfigParser
from io import BytesIO, StringIO
import json
from xml.etree.ElementTree import Element, ElementTree
from xml.parsers import expat


class AbstractCodec:

    @classmethod
    def decode(cls, *all_data:bytes, **kwargs):
        """ Decode an object from one or more byte strings.
            If more than one byte string is provided, all non-empty ones will be merged. """
        raise NotImplementedError

    def encode(self, **kwargs) -> bytes:
        """ Encode this entire object into a byte string. """
        raise NotImplementedError


class JSONDict(dict, AbstractCodec):
    """ Codec to convert Python dicts to/from JSON byte strings. """

    _ENCODE_KWARGS = {"sort_keys":    True,   # This helps some parsing and search algorithms run faster.
                      "ensure_ascii": False}  # An explicit flag is required to preserve Unicode symbols.

    @classmethod
    def decode(cls, *all_data:bytes, **kwargs):
        """ Decode each byte string to a dict and merge them in order.
            Some subclasses have high update costs, so call the constructor only after merging everything. """
        d = {}
        for data in all_data:
            d.update(cls._decode(data, **kwargs))
        return cls(d)

    @classmethod
    def _decode(cls, data:bytes, **kwargs) -> dict:
        """ JSON standard library functions are among the fastest ways to load structured data in Python. """
        return json.loads(data or b"{}", **kwargs)

    def encode(self, *, encoding:str='utf-8', **kwargs) -> bytes:
        kwargs = {**self._ENCODE_KWARGS, **kwargs}
        return json.dumps(self, **kwargs).encode(encoding)


class CSONDict(JSONDict):
    """ Codec to convert Python dicts to/from JSON strings with full-line comments. """

    @classmethod
    def _decode(cls, data:bytes, comment_prefixes=frozenset(b"#/"), **kwargs) -> dict:
        """ Decode a JSON string with single-line standalone comments. """
        # JSON doesn't care about leading or trailing whitespace, so strip every line.
        stripped_line_iter = map(bytes.strip, data.splitlines())
        # Empty lines and lines starting with a comment tag after stripping are removed before parsing.
        data_lines = [line for line in stripped_line_iter if line and line[0] not in comment_prefixes]
        return super()._decode(b"\n".join(data_lines), **kwargs)


class CFGDict(dict, AbstractCodec):
    """ Codec to convert a nested Python dict to/from a config/INI formatted byte string. """

    @classmethod
    def decode(cls, *all_data:bytes, encoding:str='utf-8', **kwargs):
        """ Decode CFG file contents into a nested dict. A two-level copy must be made to eliminate the proxies. """
        cfg = ConfigParser(**kwargs)
        for data in all_data:
            cfg.read_string(data.decode(encoding))
        d = {k: dict(v) for k, v in cfg.items() if k != "DEFAULT"}
        self = cls(d)
        self._eval_strings()
        return self

    def _eval_strings(self) -> None:
        """ Try to evaluate config strings as Python objects using AST. This fixes crap like bool('False') = True.
            Strings that are read as names will throw an error, in which case they should be left as-is. """
        for sect, page in self.items():
            for opt, val in page.items():
                try:
                    page[opt] = literal_eval(val)
                except (SyntaxError, ValueError):
                    continue

    def encode(self, *, encoding:str='utf-8', **kwargs) -> bytes:
        """ Encode this dict into a CFG file. Readability may or may not be preserved. """
        cfg = ConfigParser(**kwargs)
        cfg.read_dict(self)
        stream = StringIO()
        cfg.write(stream)
        return stream.getvalue().encode(encoding)


class XMLElement(Element, AbstractCodec):
    """ Codec for the root element of an XML file. """

    @classmethod
    def decode(cls, *all_data:bytes, **kwargs):
        """ Decode and parse XML element trees from byte strings.
            Merged documents will have the first document's root node and child nodes from all documents combined. """
        documents = [XMLStackParser()(data, **kwargs) for data in all_data if data]
        if not documents:
            return cls("null")
        self, *others = documents
        for doc in others:
            self.extend(doc)
        return self

    def encode(self, *, encoding:str='utf-8', **kwargs) -> bytes:
        """ Encode this entire object into an XML byte string. """
        stream = BytesIO()
        ElementTree(self).write(stream, encoding, **kwargs)
        return stream.getvalue()

    def encode_with(self, tag:str, *elements:Element, **kwargs) -> bytes:
        """ Make a copy of this node with all <tag> nodes and the given elements and return it encoded. """
        elem = self.__class__(self.tag, self.attrib)
        elem[:] = [e for e in self if e.tag == tag]
        elem.extend(elements)
        return elem.encode(**kwargs)


class XMLStackParser(list):
    """ Minimal parser for XML without namespaces. """

    factory: type = XMLElement
    _last: Element = None

    def __call__(self, data:bytes, encoding:str='utf-8'):
        """ Feed encoded data to parser and return element structure. """
        parser = expat.ParserCreate(encoding)
        parser.StartElementHandler = self._start
        parser.EndElementHandler = self._end
        parser.CharacterDataHandler = self._data
        parser.buffer_text = True
        parser.Parse(data, True)
        return self._last

    def _start(self, *args) -> None:
        self._last = elem = self.factory(*args)
        if self:
            self[-1].append(elem)
        self.append(elem)

    def _end(self, *args) -> None:
        self._last = self.pop()

    def _data(self, text:str) -> None:
        last = self._last
        if last is self[-1]:
            last.text = text
        else:
            last.tail = text
