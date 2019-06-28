from ast import literal_eval
from configparser import ConfigParser
from io import StringIO
import json
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


class XMLElement(dict, AbstractCodec):
    """ Generic XML element with a tree structure. """

    tag: str = "UNDEFINED"  # Tag name enclosed in <> at element start (and end, if children are included).
    text: str = ""          # Includes all text after the start tag but before the first child (if any).
    tail: str = ""          # Includes all text after the end tag but before the next element's start tag.
    _children: list         # List of all child nodes in order as read from the source document.

    def __init__(self, *elems, **attrib):
        """ Positional args are children, keyword args are attributes. """
        super().__init__(attrib)
        self._children = [*elems]

    # append, extend, iter, and len methods work on the child list. All others work on the attributes as a dict.
    def append(self, child) -> None:
        self._children.append(child)

    def extend(self, children) -> None:
        self._children += children

    def __iter__(self):
        return iter(self._children)

    def __len__(self):
        return len(self._children)

    @classmethod
    def decode(cls, *all_data:bytes, **kwargs):
        """ Decode and parse XML element trees from byte strings.
            Merged documents will have the first document's root node and child nodes from all documents combined. """
        self, *others = [cls.parse(data, **kwargs) for data in all_data if data] or [cls()]
        for doc in others:
            self.extend(doc)
        return self

    @classmethod
    def parse(cls, data:bytes, *, encoding:str='utf-8', **kwargs):
        """ Minimal parser for XML without namespace support (they are left alone, so may be parsed separately). """
        stack = []
        last = None
        def _start(tag:str, attrib:dict) -> None:
            nonlocal last
            last = cls(**attrib)
            last.tag = tag
            if stack:
                stack[-1].append(last)
            stack.append(last)
        def _end(tag:str) -> None:
            nonlocal last
            last = stack.pop()
        def _data(text:str) -> None:
            if last is stack[-1]:
                last.text = text
            else:
                last.tail = text
        parser = expat.ParserCreate(encoding, **kwargs)
        parser.buffer_text = True
        parser.StartElementHandler = _start
        parser.EndElementHandler = _end
        parser.CharacterDataHandler = _data
        parser.Parse(data, True)
        return last

    def encode(self, encoding:str='utf-8') -> bytes:
        """ Encode this entire object into an XML byte string.
            The stdlib uses an I/O stream for this, but adding strings to a list and joining them is faster. """
        s_list = ['<?xml version="1.0" encoding="', encoding, '"?>\n', *self.serialize()]
        return "".join(s_list).encode(encoding)

    def serialize(self) -> list:
        """ Recursively write strings representing this object to a list (which will be joined at the end).
            Use += when possible to avoid method call overhead. This is even faster than using f-strings. """
        tag = self.tag
        text = self.text
        tail = self.tail
        children = self._children
        s_list = ['<', tag]
        for k, v in self.items():
            s_list += ' ', k, '="', v, '"'
        if children or text:
            s_list += '>', text
            for child in children:
                s_list += child.serialize()
            s_list += '</', tag, '>', tail
        else:
            s_list += '/>', tail
        return s_list
