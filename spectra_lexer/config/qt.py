""" Module for Qt GUI config manager. """

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QLabel, QLineEdit, QMessageBox, \
    QTabWidget, QVBoxLayout, QWidget

from .spec import ConfigDict, ConfigSpec, Option, Section, SectionDict


class SectionWidget(QFrame):
    """ Config section container widget. Adds child widgets based on each option's type. """

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._layout = QFormLayout(self)
        self._getters = []  # List of config option getters with their original keys.

    def widget_bool(self, value:bool):
        """ Return a widget for true/false config options. """
        w = QCheckBox()
        w.setChecked(bool(value))
        return w, w.isChecked

    def widget_str(self, value:str):
        """ Return a widget for string config options. """
        w = QLineEdit()
        w.setText(str(value))
        return w, w.text

    def widget_int(self, value:int):
        """ Return a string-type widget that casts output values to int. """
        w, getter = self.widget_str(str(value))
        return w, (lambda: int(getter()))

    def add_option(self, opt:Option, value:object) -> None:
        """ Add a new option widget. Each supported data type uses a specific editing widget and getter method.
            Unsupported types use a string-type widget by default, though they will likely raise upon saving. """
        method = getattr(self, f'widget_{type(opt.default).__name__}', self.widget_str)
        w_option, getter = method(value)
        self._getters.append([opt.name, getter])
        w_label = QLabel(opt.title or opt.name)
        if opt.description is not None:
            w_label.setToolTip(opt.description)
            w_option.setToolTip(opt.description)
        self._layout.addRow(w_label, w_option)

    def compile(self) -> SectionDict:
        """ Compile the new config values from all widgets into a dict. Invalid settings will throw exceptions. """
        return {opt_name: getter() for opt_name, getter in self._getters}


class ConfigTabWidget(QTabWidget):

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._sections = []

    def add_section(self, sect:Section, values:SectionDict) -> None:
        """ Add a tab with child widgets based on a config <sect>ion and a matching dictionary of <values>. """
        page = SectionWidget()
        self._sections.append([sect.name, page])
        for opt in sect.options:
            page.add_option(opt, values[opt.name])
        self.addTab(page, sect.title or sect.name)

    def compile(self) -> ConfigDict:
        """ Compile the config values from all sections into a nested dict. """
        return {name: page.compile() for name, page in self._sections}


class ConfigDialog(QDialog):
    """ Qt config manager dialog with an option tab widget and standard submission form buttons. """

    WINDOW_FLAGS = Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint

    submitted = pyqtSignal([dict])  # Signal to return config values on dialog accept.

    def __init__(self, parent:QWidget=None, flags=WINDOW_FLAGS) -> None:
        super().__init__(parent, flags)
        self.setWindowTitle("Configuration Options")
        self.setMinimumSize(250, 300)
        self.setMaximumSize(250, 300)
        self._tabs = ConfigTabWidget(self)
        button_box = QDialogButtonBox(self)
        button_box.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setCenterButtons(True)
        button_box.accepted.connect(self._submit)
        button_box.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(button_box)

    def add_tabs(self, spec:ConfigSpec, options:ConfigDict) -> None:
        """ Add config section tabs based on a <spec> and a matching dictionary of config <options>. """
        for sect in spec:
            self._tabs.add_section(sect, options[sect.name])

    def _show_error(self, message:str) -> None:
        QMessageBox.warning(self, "Config Error", message)

    def _submit(self) -> None:
        """ Compile and submit the new config values on dialog accept.
            If there are one or more errors, show a popup without closing the dialog. """
        try:
            d = self._tabs.compile()
            self.submitted.emit(d)
            self.accept()
        except TypeError:
            self._show_error("One or more config types are invalid.")
        except ValueError:
            self._show_error("One or more config values are invalid.")
