""" Module for config manager. Allows editing of config values for any component. """

from typing import Any, Dict, List, Tuple

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QCheckBox, QFormLayout, QFrame, QLabel, QLayout, QLineEdit, QMessageBox, QTabWidget, \
    QVBoxLayout, QWidget

from .dialog import ToolDialog


class OptionWidgetBool(QCheckBox):
    """ Widget for true/false config options. """

    def get(self) -> bool:
        return self.isChecked()

    def set(self, value:Any) -> None:
        self.setChecked(bool(value))


class OptionWidgetStr(QLineEdit):
    """ Widget for string config options. Used as default for unknown types (nearly everything has __str__). """

    def get(self) -> str:
        return self.text()

    def set(self, value:Any) -> None:
        self.setText(str(value))


class OptionWidgetInt(OptionWidgetStr):
    """ String-type widget that casts output values to int. """

    def get(self) -> int:
        return int(self.text())


class OptionWidgets:
    """ Tracks all config option widgets and compiles their values into a dict when finished.
        Each supported option type uses a specific editing widget with basic getter and setter methods. """

    _W_TYPES = {bool: OptionWidgetBool,
                int:  OptionWidgetInt,
                str:  OptionWidgetStr}

    _widgets: List[Tuple[str, QWidget]]  # List of config option widgets by key.

    def __init__(self) -> None:
        self._widgets = []

    def generate(self, key:str, value:Any) -> QWidget:
        """ Make and return a new option widget based on the type of the original value. Only basic types are supported.
            Unsupported data types use a string-type widget by default, though they will likely raise upon saving. """
        w_option = self._W_TYPES.get(type(value), OptionWidgetStr)()
        w_option.set(value)
        self._widgets.append((key, w_option))
        return w_option

    def to_dict(self) -> Dict[str, Any]:
        """ Option values must convert back to the option's type on save. """
        return {k: w.get() for k, w in self._widgets}


class ConfigPages:
    """ Contains a tabbed page widget for each config section. """

    _pages: Dict[str, QLayout]  # Contains each tab page layout indexed by title.
    _tabs: QTabWidget           # Main tab widget.

    def __init__(self, layout:QLayout) -> None:
        """ Attach the tab widget to the layout. """
        self._pages = {}
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

    def get(self, tab:str) -> QFormLayout:
        """ Get the config page corresponding to the given tab. If it doesn't exist, make and add it. """
        if tab in self._pages:
            page = self._pages[tab]
        else:
            w_frame = QFrame()
            page = self._pages[tab] = QFormLayout(w_frame)
            self._tabs.addTab(w_frame, tab)
        return page


class ConfigDialog(ToolDialog):
    """ Outermost Qt config dialog window object. Has standard submission form buttons. """

    TITLE = "Spectra Configuration"
    SIZE = (250, 300)

    sig_accept = pyqtSignal([dict])  # Signal to return config values to the parent on dialog accept.

    _widgets: OptionWidgets  # Contains all active widgets.
    _pages: ConfigPages      # Contains all active tab pages.

    def __init__(self, *args) -> None:
        """ Create a new central tab widget from the config info rows. """
        super().__init__(*args)
        self._widgets = OptionWidgets()
        layout = QVBoxLayout(self)
        self._pages = ConfigPages(layout)
        self.add_buttons(layout)

    def add_option(self, key:str, value:Any, tab:str, label:str, description:str) -> None:
        """ Make a new widget for a config option based on these attributes:
            key - Key for the option in the final output dict. No effect on appearance.
            value - Initial value of the option. Determines the widget type.
            tab - Tab page under which to put the option.
            label - Label to display beside the option.
            description - Short description to display in a tooltip. """
        w_option = self._widgets.generate(key, value)
        page = self._pages.get(tab)
        w_label = QLabel(label)
        w_label.setToolTip(description)
        w_option.setToolTip(description)
        page.addRow(w_label, w_option)

    def accept(self) -> None:
        """ Validate all config values from each page and widget. Show a popup if there are one or more errors.
            Otherwise, send a dict with the new values on dialog accept and close the window. """
        try:
            d = self._widgets.to_dict()
            self.sig_accept.emit(d)
            super().accept()
        except TypeError:
            QMessageBox.warning(self, "Config Error", "One or more config types was invalid.")
        except ValueError:
            QMessageBox.warning(self, "Config Error", "One or more config values was invalid.")
