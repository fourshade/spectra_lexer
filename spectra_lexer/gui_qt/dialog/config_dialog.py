from typing import Callable, Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGridLayout, QLabel, QLineEdit, \
    QTabWidget, QWidget

# Each supported option type uses a specific editing widget with basic getter and setter methods.
_OPT_WIDGETS = {bool: (QCheckBox, "isChecked", "setChecked"),
                str:  (QLineEdit, "text",      "setText")}


def option_widget(val:object, opt_type:type) -> QWidget:
    """ Create a new widget for a config option based on its type. Only basic types are supported.
        If an unsupported type is given, it is handled as a string (the native format for ConfigParser). """
    w_type = opt_type if opt_type in _OPT_WIDGETS else str
    (w_factory, getter, setter) = _OPT_WIDGETS[w_type]
    w = w_factory()
    # Options are converted to the widget's native type on load, and back to the option's type on save.
    getattr(w, setter)(w_type(val))
    w.save = getattr(w, getter)
    return w


class OptionPage(QFrame):
    """ Frame widget for each tab page. Each page contains the settings for one component. """

    _widgets: Dict[str, QWidget]  # Tracks each widget with config values.

    def __init__(self, opt_dict:dict):
        """ Create a new page widget from one component's config info dict. """
        super().__init__()
        self._widgets = {}
        layout = QFormLayout()
        for (name, opt) in opt_dict.items():
            w = self._widgets[name] = option_widget(opt.val, opt.tp)
            label = QLabel(name.replace("_", " ").title())
            if opt.desc:
                w.setToolTip(opt.desc)
                label.setToolTip(opt.desc)
            layout.addRow(label, w)
        self.setLayout(layout)

    def save(self) -> dict:
        """ Gather config values from each widget and save them to a dict. """
        return {name: w.save() for (name, w) in self._widgets.items()}


class ConfigDialog(QDialog):
    """ Outermost Qt config dialog window object. """

    _pages: Dict[str, QFrame] = {}  # Tracks each widget container page with config info.
    _save_callback: Callable        # Callback to send updated settings to on dialog accept.

    def __init__(self, parent:QWidget, save_callback:Callable):
        """ Create UI elements and connect basic signals. Tabs are not created until config info is sent. """
        super().__init__(parent, Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        cancel = QDialogButtonBox.Cancel
        ok = QDialogButtonBox.Ok
        self.setObjectName("ConfigDialog")
        self.setWindowTitle("Spectra Configuration")
        self.resize(250, 300)
        self.setSizeGripEnabled(False)
        self.layout_main = QGridLayout(self)
        self.layout_main.setObjectName("layout_main")
        self.w_tabs = QTabWidget(self)
        self.w_tabs.setObjectName("w_tabs")
        self.layout_main.addWidget(self.w_tabs, 0, 0, 1, 1)
        self.w_buttons = QDialogButtonBox(self)
        self.w_buttons.setObjectName("w_buttons")
        self.w_buttons.setOrientation(Qt.Horizontal)
        self.w_buttons.setStandardButtons(cancel | ok)
        self.w_buttons.button(cancel).clicked.connect(self.reject)
        self.w_buttons.button(ok).clicked.connect(self.accept)
        self.layout_main.addWidget(self.w_buttons, 1, 0, 1, 1, Qt.AlignHCenter)
        self._save_callback = save_callback
        self.accepted.connect(self.save_settings)

    def load_settings(self, cfg_info:dict) -> None:
        """ (Re)create all tabs and widgets using config info from the dict. """
        self._pages = {}
        self.w_tabs.clear()
        for sect in sorted(cfg_info):
            page = OptionPage(cfg_info[sect])
            self._pages[sect] = page
            self.w_tabs.addTab(page, sect)

    def save_settings(self) -> None:
        """ Send a dict of all config values from each page and widget to the callback. """
        self._save_callback({sect: page.save() for (sect, page) in self._pages.items()})
