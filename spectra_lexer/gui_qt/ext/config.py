""" Module for config manager. Allows editing of config values for any component. """

from typing import Dict, Iterable, List, Tuple

from PyQt5.QtWidgets import QCheckBox, QFormLayout, QFrame, QLabel, QLayout, QLineEdit, QMessageBox, QTabWidget, \
    QVBoxLayout, QWidget

from .dialog import FormDialog
from spectra_lexer.view import ConfigItem


class OptionWidgetBool(QCheckBox):

    def get(self) -> bool:
        return self.isChecked()

    def set(self, val) -> None:
        self.setChecked(bool(val))


class OptionWidgetStr(QLineEdit):

    def get(self) -> str:
        return self.text()

    def set(self, val) -> None:
        self.setText(str(val))


class OptionWidgetInt(OptionWidgetStr):

    def get(self) -> int:
        return int(self.text())


class OptionWidgets:
    """ Tracks all config option widgets and compiles their values into a dict when finished.
        Each supported option type uses a specific editing widget with basic getter and setter methods. """

    _W_TYPES = {bool: OptionWidgetBool,
                int:  OptionWidgetInt,
                str:  OptionWidgetStr}

    _widgets: List[Tuple[str, QWidget]]  # List of config option widgets by key.

    def __init__(self):
        self._widgets = []

    def generate(self, key:str, value) -> QWidget:
        """ Make and return a new option widget based on the type of the original value.
            Unsupported data types use a string-type widget by default, though they will likely raise upon saving. """
        w_option = self._W_TYPES.get(type(value), OptionWidgetStr)()
        w_option.set(value)
        self._widgets.append((key, w_option))
        return w_option

    def to_dict(self) -> dict:
        """ Option values must convert back to the option's type on save. """
        return {k: w.get() for k, w in self._widgets}


class ConfigPages:
    """ Contains a tabbed page widget for each config section. """

    _pages: Dict[str, QLayout]  # Contains each tab page layout indexed by title.
    _tabs: QTabWidget

    def __init__(self):
        self._pages = {}
        self._tabs = QTabWidget()

    def get(self, title:str) -> QFormLayout:
        """ Get the config page corresponding to the given title. If it doesn't exist, make and add it. """
        if title in self._pages:
            page = self._pages[title]
        else:
            w_frame = QFrame()
            page = self._pages[title] = QFormLayout(w_frame)
            self._tabs.addTab(w_frame, title)
        return page

    def layout(self, parent:QWidget) -> QVBoxLayout:
        """ Attach the tab widget to a new layout and return it. """
        layout = QVBoxLayout(parent)
        layout.addWidget(self._tabs)
        return layout


class ConfigDialog(FormDialog):
    """ Outermost Qt config dialog window object. """

    TITLE = "Spectra Configuration"
    SIZE = (250, 300)

    _widgets: OptionWidgets = None

    def new_layout(self, info:Iterable[ConfigItem]=()) -> QLayout:
        """ Create a new central tab widget from the info rows.
            Make new widgets for config options based on attributes. Only basic types are supported.
            If an unsupported type is given, it is handled as a string (the native format for ConfigParser). """
        self._widgets = OptionWidgets()
        pages = ConfigPages()
        for item in info:
            w_option = self._widgets.generate(item.key, item.value)
            page = pages.get(item.title)
            w_label = QLabel(item.name)
            w_label.setToolTip(item.description)
            w_option.setToolTip(item.description)
            page.addRow(w_label, w_option)
        return pages.layout(self)

    def submit(self) -> dict:
        """ Validate all config values from each page and widget. Show a popup if there are one or more errors.
            Return a dict with the new values (not the setup info) to the callback on dialog accept. """
        try:
            return self._widgets.to_dict()
        except TypeError:
            QMessageBox.warning(self, "Config Error", "One or more config types was invalid.")
        except ValueError:
            QMessageBox.warning(self, "Config Error", "One or more config values was invalid.")
