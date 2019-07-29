""" Base module of the Spectra core package. Contains the most fundamental classes. Don't touch anything... """

from typing import List

from .command import Command, CommandGroup

ConsoleCommand = CommandGroup()


class CORE:
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the root class of the Spectra lexer component hierarchy, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program. """

    CONSOLE_COMMANDS: list = ConsoleCommand  # List of all commands directly available in the console.

    @Command
    def Load(self) -> None:
        """ Load initial data that requires engine access (unlike __init__). """
        raise NotImplementedError

    @Command
    def Exit(self) -> None:
        """ Exit the application entirely. """
        raise NotImplementedError

    @Command
    def COREDebug(self, components:list) -> None:
        """ Send every component definition in the application to debug components. """
        raise NotImplementedError

    @Command
    def COREStatus(self, status:str) -> None:
        """ Display a plaintext status message (non-error). """
        raise NotImplementedError

    @Command
    def COREException(self, exc:Exception) -> bool:
        """ Handle a top-level exception (typically by logging or displaying it). Return True if successful. """
        raise NotImplementedError

    @Command
    def COREConsoleOpen(self, *, interactive:bool=True, **kwargs) -> None:
        """ Open the console with all engine commands, each wrapped in the original function info. """
        raise NotImplementedError

    @Command
    def COREConsoleInput(self, text_in:str) -> None:
        """ Process a string of input text as Python code and write the result to SYSConsoleOutput. """
        raise NotImplementedError

    @Command
    def SYSConsoleOutput(self, text_out:str) -> None:
        """ Console output is written here as if to a stream. Forwards to stdout by default. """
        raise NotImplementedError

    @Command
    def COREFileLoad(self, *patterns:str, ignore_missing:bool=False) -> List[bytes]:
        """ Read one or more files, expanding wildcard patterns. Missing files may be ignored instead of raising. """
        raise NotImplementedError

    @Command
    def COREFileSave(self, data:bytes, filename:str) -> None:
        """ Save encoded bytes to a file. """
        raise NotImplementedError
