from spectra_lexer import Component
from .codecs import CodecDatabase, CFGCodec, CSONCodec, JSONCodec
from .resource import Resource, resources_from_patterns, resource_from_string

# List of all codec subclasses. One of each must be instantiated in the master dict.
_ALL_CODECS = [CFGCodec, JSONCodec, CSONCodec]


class FileHandler(Component):
    """ Main component for file I/O operations and dialogs. Directs actual I/O routines to codecs. """

    _codecs: CodecDatabase  # Holds decoders/encoders for each supported file format.

    def __init__(self):
        super().__init__()
        self._codecs = CodecDatabase(_ALL_CODECS)

    @on("file_load")
    def load(self, filename:str) -> dict:
        """ Attempt to load and decode a single resource (no patterns) given by name. """
        return self._decode(resource_from_string(filename))

    @on("file_load_all")
    def load_all(self, *patterns:str) -> list:
        """ Attempt to expand all patterns and decode all files in the arguments and return a list. """
        return list(map(self._decode, resources_from_patterns(*patterns)))

    @on("file_save")
    def save(self, filename:str, d:dict) -> None:
        """ Attempt to encode and save a resource to a file given by name. """
        return self._encode(resource_from_string(filename), d)

    @on("file_get_extensions")
    def get_exts(self) -> list:
        """ Return a list of all valid file extensions (including the dot). """
        return self._codecs.get_formats()

    def _decode(self, f:Resource) -> dict:
        """ Read and decode a string resource. """
        decoder = self._codecs.get_decoder(f)
        d = decoder(f.read())
        return d

    def _encode(self, f:Resource, d:dict) -> None:
        """ Encode a dict into a string resource and write it. """
        encoder = self._codecs.get_encoder(f)
        f.write(encoder(d))
