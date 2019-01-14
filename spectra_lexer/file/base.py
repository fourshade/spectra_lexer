from spectra_lexer import Component, on, respond_to
from spectra_lexer.file.codecs import CODECS, decode, encode
from spectra_lexer.file.resource import resource_from_string, resources_from_patterns


class FileHandler(Component):
    """ Engine wrapper for file I/O operations. Directs engine commands to module-level functions. """

    ROLE = "file"

    @respond_to("file_load")
    def load(self, *patterns:str) -> list:
        """ Attempt to expand all patterns and decode all files in the arguments and return a list. """
        return list(map(decode, resources_from_patterns(*patterns)))

    @on("file_save")
    def save(self, filename:str, obj:object) -> None:
        """ Attempt to encode and save a resource to a file given by name. """
        return encode(resource_from_string(filename), obj)

    @respond_to("file_get_supported_exts")
    def get_supported_exts(self) -> list:
        """ Return all valid file extensions (including the dot) for encodable/decodable dict formats. """
        return list(CODECS)
