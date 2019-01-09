from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QLabel, QLineEdit, \
    QScrollArea, QWidget

from spectra_lexer.gui_qt.config.config_dialog_ui import Ui_ConfigDialog

# Each supported option type uses a specific editing widget with basic getter and setter methods.
OPT_WIDGETS = {bool: (QCheckBox, QCheckBox.isChecked, QCheckBox.setChecked),
               str:  (QLineEdit, QLineEdit.text,      QLineEdit.setText)}


def option_widget(val) -> QWidget:
    """ Create a new widget for a config option based on its type. Only basic types are supported.
        If an unsupported type is given, it is handled as a string (the native format for ConfigParser). """
    opt_type = type(val)
    w_type = opt_type if opt_type in OPT_WIDGETS else str
    (w_factory, getter, setter) = OPT_WIDGETS[w_type]
    w = w_factory()
    # Options must be converted to the widget's native type on load, and back to the option's type on save.
    setter(w, w_type(val))
    w.save = lambda: opt_type(getter(w))
    return w


class OptionPage(QFrame):
    """ Frame widget for each tab page. Each page contains the settings for one component. """

    _widgets: dict  # Tracks each widget with config values.

    def __init__(self, opt_dict:dict):
        super().__init__()
        self._widgets = {}
        layout = QFormLayout()
        for (opt, val) in opt_dict.items():
            w = option_widget(val)
            self._widgets[opt] = w
            layout.addRow(QLabel(opt), w)
        self.setLayout(layout)

    def save(self) -> dict:
        """ Gather config settings from each widget and save them to a dict. """
        return {opt: w.save() for (opt, w) in self._widgets.items()}


class ConfigDialog(QDialog, Ui_ConfigDialog):
    """ Outermost Qt config dialog window object. """

    _pages: dict = {}  # Tracks each widget container page with config values.

    def __init__(self, parent:QWidget=None):
        """ Create UI elements and connect basic signals. Tabs are not created until config info is sent. """
        super().__init__(parent, Qt.Dialog)
        self.setupUi(self)
        self._connect_button("Ok", self.accept)
        self._connect_button("Apply", self.accept)
        self._connect_button("Cancel", self.reject)

    def _connect_button(self, button:str, slot:pyqtSlot) -> None:
        self.w_buttons.button(getattr(QDialogButtonBox, button)).clicked.connect(slot)

    def load_settings(self, cfg_dict:dict) -> None:
        """ (Re)create all tabs and widgets using config settings from the dict. """
        self._pages = {}
        self.w_tabs.clear()
        for (sect, opt_dict) in cfg_dict.items():
            page = OptionPage(opt_dict)
            self._pages[sect] = page
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(page)
            self.w_tabs.addTab(scroll_area, sect)

    def save_settings(self) -> dict:
        """ Gather all config settings from each page and widget and save them to a nested dict. """
        return {sect: page.save() for (sect, page) in self._pages.items()}
