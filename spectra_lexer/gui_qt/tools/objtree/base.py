from pkgutil import get_data

from .impl import ObjectTreeDialog
from .resources import IconData, RootDict
from ..base import GUIQT_TOOL
from ..dialog import DialogContainer

_ICON_PATH = "/treeicons.svg"  # File with all object tree icons.


class ObjectTreeTool(GUIQT_TOOL):
    """ Component for interactive tree operations. The fields are expensive to create and probably unused
        most of the time, so each one is computed only on first dialog request. """

    _dialog: DialogContainer
    root_dict: dict = None
    icon_data: IconData = None
    _last_exception: Exception = None  # Holds last exception caught from the engine.

    def __init__(self) -> None:
        self._dialog = DialogContainer(ObjectTreeDialog)

    def TOOLTreeOpen(self) -> None:
        """ Add the last engine exception to the root dict if any were caught. """
        if self.root_dict is None:
            self.root_dict = RootDict(self.ALL_COMPONENTS)
            self.icon_data = IconData(get_data(__package__, _ICON_PATH))
        if self._last_exception is not None:
            self.root_dict["last_exception"] = self._last_exception
        self._dialog.open(self.WINDOW, self.root_dict, self.icon_data)

    def HandleException(self, exc:Exception) -> bool:
        """ Save the last exception for introspection. If THAT fails, the system is beyond help. """
        self._last_exception = exc
        return True
