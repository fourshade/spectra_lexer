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

    @on("file_add_dialog")
    def add_dialog(self, d_type:str, **kwargs) -> None:
        """ Add a basic file dialog command for a data type with all valid file extensions (including the dot). """
        title_msg = f"Load {d_type.title()}"
        filter_msg = f"Supported file formats (*{' *'.join(self._codecs.get_formats())})"
        self.engine_call("new_menu_item", "File", title_msg + "...",
                         "new_file_dialog", d_type, title_msg + " Dictionaries", filter_msg, **kwargs)

    def _decode(self, f:Resource) -> dict:
        """ Read and decode a string resource. """
        decoder = self._codecs.get_decoder(f)
        d = decoder(f.read())
        return d

    def _encode(self, f:Resource, d:dict) -> None:
        """ Encode a dict into a string resource and write it. """
        encoder = self._codecs.get_encoder(f)
        f.write(encoder(d))
