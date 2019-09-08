from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QMessageBox, QSlider, QToolTip, QVBoxLayout, QWidget

from .dialog import ToolDialog
from spectra_lexer.steno import IndexInfo


STARTUP_MESSAGE = """
<p>In order to cross-reference examples of specific steno rules, this program must create an index
using your Plover dictionary. The default file size is around 10 MB, and can take anywhere
between 5 seconds and 5 minutes depending on the speed of your machine and hard disk.
Would you like to create one now? You will not be asked again.</p>
<p>(If you cancel, all other features will still work. You can always create the index later from
the Tools menu, and can expand it from the default size as well if it is not sufficient).</p>"""


def default_index_dialog(parent:QWidget) -> int:
    """ Present a dialog for the user to make a default-sized index. Return that size on accept, or 0 on cancel. """
    yes, no = QMessageBox.Yes, QMessageBox.No
    button = QMessageBox.question(parent, "Make Index", STARTUP_MESSAGE, yes | no)
    return (button == yes) * IndexInfo.DEFAULT_SIZE


class SliderIndexDialog(ToolDialog):
    """ Qt dialog window with an interactive slider that submits a positive number on accept, or 0 on cancel. """

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._slider = QSlider(self)  # Horizontal slider.

    def setup(self) -> None:
        self.setup_window("Choose Index Size", 360, 320)
        heading_label = QLabel(self)
        heading_label.setWordWrap(True)
        heading_lines = ['Please choose a size for the new index.', *IndexInfo.SIZE_DESCRIPTIONS]
        heading_text = '<br><br>'.join(heading_lines)
        heading_label.setText(heading_text)
        self._slider.setMinimum(IndexInfo.MINIMUM_SIZE)
        self._slider.setMaximum(IndexInfo.MAXIMUM_SIZE)
        self._slider.setValue(IndexInfo.DEFAULT_SIZE)
        self._slider.setOrientation(Qt.Horizontal)
        self._slider.setTickPosition(QSlider.TicksBelow)
        self._slider.setTickInterval(1)
        self._slider.valueChanged.connect(self.new_slider_value)
        desc_label = QLabel(self)
        desc_label.setWordWrap(True)
        desc_label.setText(f"<p align='justify'>{IndexInfo.SIZE_WARNING}</p>")
        layout = QVBoxLayout(self)
        layout.addWidget(heading_label)
        layout.addWidget(self._slider)
        layout.addWidget(desc_label)
        layout.addWidget(self.button_box())

    def accept(self) -> None:
        """ Emit the slider position on accept and close the window. """
        value = self._slider.value()
        self.sig_accept.emit(value)
        super().accept()

    def new_slider_value(self, value:int) -> None:
        """ Show a tooltip with the current numerical value when the slider is moved. """
        QToolTip.showText(self.pos() + self._slider.pos(), str(value), self._slider)
