from typing import Callable, Type

from spectra_lexer.core import Command, CORE, Option
from spectra_lexer.types.codec import AbstractCodec

CmdlineOption = Option()


class SYS(CORE):
    """ Simple interface definition for general system commands and resources with no specific category. """

    CMDLINE_INFO: Option = CmdlineOption  # Keeps track of command line options in a master dict.

    @Command
    def SYSStatus(self, status:str) -> None:
        """ Display a plaintext status message (non-error). """
        raise NotImplementedError

    @Command
    def SYSTraceback(self, tb_text:str) -> None:
        """ Display an exception traceback in string form. """
        raise NotImplementedError

    @Command
    def SYSConsoleOpen(self, *args, interactive:bool=True) -> str:
        """ Open the console with all engine commands, each wrapped in the original function info. """
        raise NotImplementedError

    @Command
    def SYSConsoleInput(self, text_in:str) -> str:
        """ Process a string of input text and return any resulting output. """
        raise NotImplementedError

    @Command
    def SYSConsoleBatch(self, *commands:str) -> int:
        """ Run the given commands in batch mode while timing execution and exit. """
        raise NotImplementedError

    @Command
    def SYSConsoleRepl(self, input_cb:Callable[[], str]=input) -> int:
        """ Run the console in an interactive read-eval-print loop. """
        raise NotImplementedError

    @Command
    def SYSFileLoad(self, codec_cls:Type[AbstractCodec], *patterns:str, ignore_missing:bool=False, **kwargs):
        """ Load one or more files and decode/merge them using a suitable codec.
            Wildcard patterns are expanded before reading. Missing files may be ignored instead of raising. """
        raise NotImplementedError

    @Command
    def SYSFileSave(self, obj:AbstractCodec, filename:str, **kwargs) -> None:
        """ Save an encodable object to a file. """
        raise NotImplementedError
