from typing import Callable, Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGridLayout, QLabel, QLineEdit, \
    QTabWidget, QWidget, QMessageBox

# Each supported option type uses a specific editing widget with basic getter and setter methods.
_W_TYPES = {bool: (QCheckBox, QCheckBox.isChecked, QCheckBox.setChecked),
            str:  (QLineEdit, QLineEdit.text,      QLineEdit.setText)}


def save_dict(d:dict) -> dict:
    """ Call the save method on all values in a dict and replace them in a new dict with their return values. """
    return {k: v.save() for k, v in d.items()}


class OptionRow(list):

    def __init__(self, val:object, opt_tp:type, label:str, desc:str):
        """ Create a new widget row for a config option based on its attributes. Only basic types are supported.
            If an unsupported type is given, it is handled as a string (the native format for ConfigParser). """
        w_tp = opt_tp if opt_tp in _W_TYPES else str
        w_factory, getter, setter = _W_TYPES[w_tp]
        w = w_factory()
        w.setToolTip(desc)
        w_label = QLabel(label)
        w_label.setToolTip(desc)
        super().__init__([w_label, w])
        # Option values must convert to the widget's native type on load, and back to the option's type on save.
        setter(w, w_tp(val))
        self.save = lambda: opt_tp(getter(w))


class OptionPage(QFrame):

    def __init__(self, opt_dict:dict):
        """ Create a new page widget from one component's config info dict. """
        super().__init__()
        rows = {name: OptionRow(*opt) for name, opt in opt_dict.items()}
        layout = QFormLayout(self)
        for name, row in rows.items():
            layout.addRow(*row)
        self.save = lambda: save_dict(rows)


class ConfigDialog(QDialog):
    """ Outermost Qt config dialog window object. """

    def __init__(self, parent:QWidget, submit_cb:Callable, info:Dict[str, dict]):
        """ Create UI elements using info from the dict, connect basic signals, and set the callback. """
        super().__init__(parent, Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle("Spectra Configuration")
        self.resize(250, 300)
        self.setSizeGripEnabled(False)
        pages = {sect: OptionPage(info[sect]) for sect in sorted(info)}
        w_tabs = QTabWidget(self)
        for sect, page in pages.items():
            w_tabs.addTab(page, sect)
        cancel = QDialogButtonBox.Cancel
        ok = QDialogButtonBox.Ok
        w_buttons = QDialogButtonBox(self)
        w_buttons.setStandardButtons(cancel | ok)
        w_buttons.button(cancel).clicked.connect(self.reject)
        w_buttons.button(ok).clicked.connect(self.accept)
        layout_main = QGridLayout(self)
        layout_main.addWidget(w_tabs, 0, 0, 1, 1)
        layout_main.addWidget(w_buttons, 1, 0, 1, 1, Qt.AlignHCenter)
        self.save = lambda: submit_cb(save_dict(pages))

    def accept(self) -> None:
        """ Validate all config values from each page and widget. Show a popup if there are one or more errors.
            Send a dict with the new values (not the setup info) to the callback on dialog accept, then close. """
        try:
            self.save()
            return super().accept()
        except TypeError:
            QMessageBox.warning(self, "Config Error", "One or more config types was invalid.")
        except ValueError:
            QMessageBox.warning(self, "Config Error", "One or more config values was invalid.")
