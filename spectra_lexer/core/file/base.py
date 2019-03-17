from .codecs import Codec
from .resource import Resource
from spectra_lexer import Component


class FileHandler(Component):
    """ Main component for file I/O operations and dialogs. Directs actual I/O routines to codecs. """

    @on("file_load")
    def load(self, filename:str) -> dict:
        """ Attempt to load and decode a single resource (no patterns) given by name. """
        return self._decode(Resource.from_string(filename))

    @on("file_load_all")
    def load_all(self, *patterns:str) -> list:
        """ Attempt to expand all patterns and decode all files in the arguments and return a list. """
        return [self._decode(f) for p in patterns for f in Resource.from_pattern(p)]

    @on("file_save")
    def save(self, filename:str, d:dict) -> None:
        """ Attempt to encode and save a resource to a file given by name. """
        return self._encode(Resource.from_string(filename), d)

    get_formats = on("file_get_extensions")(Codec.get_formats)

    def _decode(self, f:Resource) -> dict:
        """ Read and decode a string resource. """
        decoder = Codec.get_decoder(f)
        d = decoder(f.read())
        return d

    def _encode(self, f:Resource, d:dict) -> None:
        """ Encode a dict into a string resource and write it. """
        encoder = Codec.get_encoder(f)
        f.write(encoder(d))
