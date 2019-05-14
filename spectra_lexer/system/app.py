import sys
from typing import Any, Hashable, List, Tuple

from spectra_lexer import system
from spectra_lexer.core import Component, Resource
from spectra_lexer.core.app import Application
from spectra_lexer.core.group import ComponentGroup


class SYSApp:

    class CmdlineArgs:
        """ Contains command line arguments from sys.argv (excluding the script name). """
        args: List[str] = Resource()

    class Components:
        """ Contains every component definition in the application. """
        components: List[Component] = Resource()

    class AssetPath:
        """ Root directory for application assets. """
        asset_path: str = Resource()

    class UserPath:
        """ Root directory for user data files. """
        user_path: str = Resource()


class SystemApplication(Application, SYSApp):
    """ Abstract base application class with essential system functionality. """

    def _class_paths(self) -> list:
        return [system]

    def _global_commands(self, components:ComponentGroup) -> List[Tuple[Hashable, Any]]:
        """ System components require the command line arguments and file paths.
            The full component list is also useful for debugging.  """
        path = self._root_path()
        return [*super()._global_commands(components),
                (self.CmdlineArgs, sys.argv[1:]),
                (self.AssetPath, path),
                (self.UserPath, path),
                (self.Components, list(components))]

    @classmethod
    def _root_path(cls):
        """ The name of the class's root package is used as a default path for built-in assets and user files. """
        return cls.__module__.split(".", 1)[0]
