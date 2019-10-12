""" Module for config manager. Allows editing of config values for any component. """

from typing import Any, Callable, Iterable

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QCheckBox, QDialogButtonBox, QFormLayout, QFrame, QLabel, QLineEdit, QMessageBox, \
    QTabWidget, QVBoxLayout, QWidget

from .dialog import ToolDialog

from spectra_lexer.option import ConfigItem


class OptionWidgets:
    """ Tracks config options by key and creates a Qt editing widget for each one based on its type. """

    def __init__(self) -> None:
        self._widgets = {}  # Dict of config option widgets by their original keys.

    def generate(self, key:str, value:Any) -> QWidget:
        """ Make and return a new option widget based on the type of the original value. Only basic types are supported.
            Each supported option type uses a specific editing widget with basic getter and setter methods.
            Unsupported data types use a string-type widget by default, though they will likely raise upon saving. """
        cls_name = "OptionWidget" + type(value).__name__.title()
        w_type = getattr(self, cls_name, self.OptionWidgetStr)
        self._widgets[key] = w_option = w_type()
        w_option.set(value)
        return w_option

    def compile(self) -> dict:
        """ Save all option values to a dict. They must be converted back to the original type if different. """
        return {k: w.get() for k, w in self._widgets.items()}

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


class ConfigPages:
    """ Contains a tabbed page widget for each config section. """

    def __init__(self, tabs:QTabWidget) -> None:
        self._pages = {}   # Contains each tab page layout indexed by title.
        self._tabs = tabs  # Main tab widget.

    def add_widget(self, w_option:QWidget, tab:str, name:str, tooltip:str) -> None:
        """ Add a new widget to the config page under <tab>. """
        w_label = QLabel(name)
        w_label.setToolTip(tooltip)
        w_option.setToolTip(tooltip)
        page = self._get_page(tab)
        page.addRow(w_label, w_option)

    def _get_page(self, tab:str) -> QFormLayout:
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

    _sig_accept = pyqtSignal([dict])  # Signal to return config values on dialog accept.

    title = "Spectra Configuration"
    width = 250
    height = 300

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._widgets = OptionWidgets()  # Contains all active config option widgets.

    def setup(self, options_callback:Callable[[dict], None], info:Iterable[ConfigItem]) -> None:
        """ Create a new central tab widget for the config info rows.
            Make a new widget for each config option in <info> based on these attributes:
                key - Key for the option in the final output dict. No effect on appearance.
                value - Initial value of the option. Determines the widget type.
                tab - Tab page under which to put the option.
                label - Label to display beside the option.
                description - Short description to display in a tooltip. """
        tabs = QTabWidget()
        pages = ConfigPages(tabs)
        for item in info:
            w_option = self._widgets.generate(item.key, item.value)
            pages.add_widget(w_option, item.title, item.name, item.description)
        button_box = QDialogButtonBox(self)
        button_box.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setCenterButtons(True)
        button_box.accepted.connect(self._check_accept)
        button_box.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(button_box)
        self._sig_accept.connect(options_callback)

    def _check_accept(self) -> None:
        """ Compile the new config values into a dict on dialog accept and close the window.
            If there are one or more errors, show a popup without closing the window. """
        try:
            d = self._widgets.compile()
            self._sig_accept.emit(d)
            self.accept()
        except TypeError:
            self._show_error("One or more config types are invalid.")
        except ValueError:
            self._show_error("One or more config values are invalid.")

    def _show_error(self, message:str) -> None:
        QMessageBox.warning(self, "Config Error", message)
