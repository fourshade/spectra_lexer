from typing import Callable, Dict

from PyQt5.QtWidgets import QCheckBox, QFormLayout, QFrame, QLabel, QLineEdit, QMessageBox, QTabWidget, QVBoxLayout, \
    QWidget

from spectra_lexer.gui_qt.tools.dialog import FormDialog

# Each supported option type uses a specific editing widget with basic getter and setter methods.
_W_TYPES = {bool: (QCheckBox, QCheckBox.isChecked, QCheckBox.setChecked),
            str:  (QLineEdit, QLineEdit.text,      QLineEdit.setText)}


def _save_dict(d:dict) -> dict:
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
        self.save = lambda: _save_dict(rows)


class ConfigDialog(FormDialog):
    """ Outermost Qt config dialog window object. """

    TITLE = "Spectra Configuration"
    SIZE = (250, 300)

    w_tabs: QTabWidget = None  # Central widget of the dialog window; holds every setting among multiple tabs.

    def __init__(self, parent:QWidget, submit_cb:Callable, info:Dict[str, dict]):
        """ Create UI elements using info from the dict and set the save callback. """
        super().__init__(parent, submit_cb)
        pages = {sect: OptionPage(info[sect]) for sect in sorted(info)}
        for sect, page in pages.items():
            self.w_tabs.addTab(page, sect)
        self.save = lambda: _save_dict(pages)

    def upper_layout(self, layout:QVBoxLayout) -> None:
        """ Make and add the central widget to the top of the layout. """
        self.w_tabs = QTabWidget(self)
        layout.addWidget(self.w_tabs)

    def submit(self) -> dict:
        """ Validate all config values from each page and widget. Show a popup if there are one or more errors.
            Return a dict with the new values (not the setup info) to the callback on dialog accept. """
        try:
            return self.save()
        except TypeError:
            QMessageBox.warning(self, "Config Error", "One or more config types was invalid.")
        except ValueError:
            QMessageBox.warning(self, "Config Error", "One or more config values was invalid.")
