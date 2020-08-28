""" Module for Qt GUI config manager. """

from typing import Any

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QLabel, QLineEdit, QMessageBox, \
    QTabWidget, QVBoxLayout, QWidget


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


class ConfigDialog(QDialog):
    """ Qt config dialog window tool. Adds standard submission form buttons. """

    _sig_accept = pyqtSignal([dict])  # Signal to return config values on dialog accept.

    DEFAULT_FLAGS = Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint

    def __init__(self, parent=None, flags=DEFAULT_FLAGS) -> None:
        super().__init__(parent, flags)
        self.setWindowTitle("Configuration Options")
        self.setMinimumSize(250, 300)
        self.setMaximumSize(250, 300)
        self._tabs = QTabWidget()        # Central tab widget for the config info rows.
        self._widgets = OptionWidgets()  # Contains all active config option widgets.
        self._pages = {}                 # Contains each tab page layout indexed by name.
        button_box = QDialogButtonBox(self)
        button_box.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setCenterButtons(True)
        button_box.accepted.connect(self._check_accept)
        button_box.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(button_box)
        self.call_on_options_accept = self._sig_accept.connect

    def add_option(self, key:str, value:Any, sect_name:str, opt_name:str, description="") -> None:
        """ Create a widget for a new config info row based on these attributes:
            key - Key for the option in the final output dict. No effect on appearance.
            value - Initial value of the option. Determines the widget type.
            sect_name - Name of tab page under which to put the option.
            opt_name - Name to display beside the option.
            description - Optional; short description to display in a tooltip. """
        w_option = self._widgets.generate(key, value)
        w_label = QLabel(opt_name)
        if description:
            w_label.setToolTip(description)
            w_option.setToolTip(description)
        page = self._get_page(sect_name)
        page.addRow(w_label, w_option)

    def _get_page(self, name:str) -> QFormLayout:
        """ Get the config page corresponding to the given name. If it doesn't exist, make and add it. """
        if name in self._pages:
            page = self._pages[name]
        else:
            w_frame = QFrame()
            page = self._pages[name] = QFormLayout(w_frame)
            self._tabs.addTab(w_frame, name)
        return page

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
