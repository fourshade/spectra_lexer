from xml.parsers import expat


class XMLElement(dict):
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
    def decode(cls, data:bytes, *, encoding:str='utf-8', **kwargs):
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
        s_list = ['<?xml version="1.0" encoding="', encoding, '"?>\n']
        self.serialize(s_list)
        return "".join(s_list).encode(encoding)

    def serialize(self, s_list:list, _iter=dict.__iter__) -> None:
        """ Recursively write strings representing this object to a list (which will be joined at the end).
            Use += when possible to avoid method call overhead. This is even faster than using f-strings. """
        tag = self.tag
        text = self.text
        tail = self.tail
        children = self._children
        s_list += '<', tag
        for k in _iter(self):
            s_list += ' ', k, '="', self[k], '"'
        if children or text:
            s_list += '>', text
            for child in children:
                child.serialize(s_list)
            s_list += '</', tag, '>', tail
        else:
            s_list += '/>', tail
