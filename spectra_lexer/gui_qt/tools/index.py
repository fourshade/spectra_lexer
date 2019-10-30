from typing import Callable

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialogButtonBox, QLabel, QMessageBox, QSlider, QToolTip, QVBoxLayout, QWidget

from .dialog import ToolDialog

from spectra_lexer.search import ExampleIndexInfo

INDEX_STARTUP_MESSAGE = """<p>
In order to cross-reference examples of specific steno rules, this program must create an index
using your Plover dictionary. The default file size is around 10 MB, and can take anywhere
between 5 seconds and 5 minutes depending on the speed of your machine and hard disk.
Would you like to create one now? You will not be asked again.
</p><p>
(If you cancel, all other features will still work. You can always create the index later from
the Tools menu, and can expand it from the default size as well if it is not sufficient).
</p>"""

INDEX_SIZE_WARNING = """<p align='justify'>
An extremely large index is not necessarily more useful.
The index is created from the Plover dictionary, which is very large
(about 150,000 translations) with many useless and even erroneous entries.
As the index grows, so does the loading time,
and past a certain point the garbage will start to crowd out useful information.
Unless you are doing batch analysis, there is little benefit to a maximum-sized index.
</p>"""


class IndexSizeSlider(QSlider):
    """ Qt interactive slider that displays its value in a tooltip when moved. """

    def sliderChange(self, change:int) -> None:
        """ Show a tooltip with the current numerical value when the slider is moved. """
        if change == self.SliderValueChange:
            global_pos = self.parentWidget().pos() + self.pos()
            QToolTip.showText(global_pos, str(self.value()), self)
        super().sliderChange(change)


class IndexSizeDialog(ToolDialog):
    """ Qt dialog window with an interactive slider that submits a positive number on accept, or 0 on cancel. """

    _sig_accept = pyqtSignal([int])  # Signal to return the index size on dialog accept.

    title = "Choose Index Size"
    width = 360
    height = 320

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._slider = IndexSizeSlider(self)  # Horizontal slider widget.

    def setup(self, size_callback:Callable[[int], None], info:ExampleIndexInfo) -> None:
        heading_label = QLabel(self)
        heading_label.setWordWrap(True)
        heading_lines = ['Please choose a size for the new index.', *info.size_descriptions()]
        heading_text = '<br><br>'.join(heading_lines)
        heading_label.setText(heading_text)
        self._slider.setMinimum(info.minimum_size())
        self._slider.setMaximum(info.maximum_size())
        self._slider.setValue(info.default_size())
        self._slider.setOrientation(Qt.Horizontal)
        self._slider.setTickPosition(QSlider.TicksBelow)
        self._slider.setTickInterval(1)
        desc_label = QLabel(self)
        desc_label.setWordWrap(True)
        desc_label.setText(INDEX_SIZE_WARNING)
        button_box = QDialogButtonBox(self)
        button_box.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setCenterButtons(True)
        button_box.accepted.connect(self.check_accept)
        button_box.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(heading_label)
        layout.addWidget(self._slider)
        layout.addWidget(desc_label)
        layout.addWidget(button_box)
        self._sig_accept.connect(size_callback)

    def check_accept(self) -> None:
        """ Emit the slider position on accept and close the window. """
        value = self._slider.value()
        self._sig_accept.emit(value)
        self.accept()
