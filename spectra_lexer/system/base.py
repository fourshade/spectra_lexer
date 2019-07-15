from typing import List

from spectra_lexer.core import Command, CommandGroup, CORE, OptionGroup

CmdlineOption = OptionGroup()
ConsoleCommand = CommandGroup()


class SYS(CORE):
    """ Simple interface definition for general system commands and resources with no specific category. """

    CMDLINE_INFO: list = CmdlineOption       # List of info for every command line option.
    CONSOLE_COMMANDS: list = ConsoleCommand  # List of all commands directly available in the console.

    @Command
    def SYSStatus(self, status:str) -> None:
        """ Display a plaintext status message (non-error). """
        raise NotImplementedError

    @Command
    def SYSTraceback(self, tb_text:str) -> None:
        """ Display an exception traceback in string form. """
        raise NotImplementedError

    @Command
    def SYSConsoleOpen(self, *, interactive:bool=True, **kwargs) -> None:
        """ Open the console with all engine commands, each wrapped in the original function info. """
        raise NotImplementedError

    @Command
    def SYSConsoleInput(self, text_in:str) -> None:
        """ Process a string of input text as Python code and write the result to SYSConsoleOutput. """
        raise NotImplementedError

    @Command
    def SYSConsoleOutput(self, text_out:str) -> None:
        """ Console output is written here as if to a stream. Forwards to stdout by default. """
        raise NotImplementedError

    @Command
    def SYSFileLoad(self, *patterns:str, ignore_missing:bool=False) -> List[bytes]:
        """ Read one or more files, expanding wildcard patterns. Missing files may be ignored instead of raising. """
        raise NotImplementedError

    @Command
    def SYSFileSave(self, data:bytes, filename:str) -> None:
        """ Save encoded bytes to a file. """
        raise NotImplementedError
