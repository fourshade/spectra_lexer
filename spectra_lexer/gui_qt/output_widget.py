from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QWidget

from spectra_lexer.gui_qt.output_widget_ui import Ui_OutputWidget
from spectra_lexer.output import LexerOutput


class OutputWidget(QWidget, Ui_OutputWidget):
    """
    Container widget that holds all output display elements.

    Children:
    w_title - QLineEdit, displays mapping of keys to word.
    w_text -  OutputTextWidget, displays plaintext breakdown grid.
    w_info  - OutputInfoWidget, displays rule description and steno board diagram.
        w_desc  - QLineEdit, displays rule description.
        w_board - QWidget, displays steno board diagram.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def show_status_message(self, msg:str) -> None:
        """ Show a message in the title bar. """
        self.w_title.setText(msg)

    def send_output(self, out:LexerOutput) -> None:
        """ Compute and send the given lexer format to all necessary child widgets. """
        self.w_title.setText(out.title)
        self.w_text.set_output(out)
        # For a new format, send the full set of keys and description as a rule signal.
        self.send_rule_info(out.keys, out.desc)

    @pyqtSlot(str, str)
    def send_rule_info(self, keys:str, desc:str) -> None:
        """ Send the given rule info to the info widgets. """
        self.w_desc.setText(desc)
        self.w_board.show_keys(keys)
