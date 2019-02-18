from spectra_lexer import Component, on, respond_to
from spectra_lexer.file.codecs import CodecDatabase
from spectra_lexer.file.codecs.cfg import CFGCodec
from spectra_lexer.file.codecs.json import CSONCodec, JSONCodec
from spectra_lexer.file.resource import Resource, resource_from_string, resources_from_patterns

# List of all codec subclasses. One of each must be instantiated in the master dict.
_ALL_CODECS = [CFGCodec, JSONCodec, CSONCodec]


class FileHandler(Component):
    """ Engine wrapper for file I/O operations. Directs engine commands to module-level functions. """

    ROLE = "file"

    _codecs: CodecDatabase  # Holds decoders/encoders for each supported file format.

    def __init__(self):
        super().__init__()
        self._codecs = CodecDatabase(_ALL_CODECS)

    @respond_to("file_load")
    def load(self, *patterns:str) -> list:
        """ Attempt to expand all patterns and decode all files in the arguments and return a list. """
        return list(map(self._decode, resources_from_patterns(*patterns)))

    @on("file_save")
    def save(self, filename:str, d:dict) -> None:
        """ Attempt to encode and save a resource to a file given by name. """
        return self._encode(resource_from_string(filename), d)

    @respond_to("file_get_supported_exts")
    def get_supported_exts(self) -> list:
        """ Return all valid file extensions (including the dot) for encodable/decodable dict formats. """
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
