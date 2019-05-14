""" Base module of the Spectra core package. Contains the most fundamental classes. Don't touch anything... """

from .command import Command


class CORE:
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the root class of the Spectra lexer component hierarchy, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program. """

    @Command
    def Load(self) -> None:
        """ Load initial data that requires engine access (unlike __init__). """
        raise NotImplementedError

    @Command
    def Exception(self, *exc_args) -> bool:
        """ Handle a top-level exception (typically by logging or displaying it). Return True if successful. """
        raise NotImplementedError

    @Command
    def Exit(self) -> None:
        """ Exit the application entirely. """
        raise NotImplementedError
