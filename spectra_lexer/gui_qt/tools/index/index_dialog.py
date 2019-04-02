from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QLayout, QSlider, QToolTip, QVBoxLayout

from spectra_lexer.gui_qt.tools.dialog import FormDialog

_HEADING_TEXT = """
<p>Please choose the size for the new index. The relative size factor is a number between 1 and 20:</p>
<p>size = 1: includes nothing.</p>
<p>size = 10: fast index with relatively simple words.</p>
<p>size = 12: average-sized index (default).</p>
<p>size = 15: slower index with more advanced words.</p>
<p>size = 20: includes everything.</p>"""

_BODY_TEXT = """
<p align="justify">An extremely large index is not necessarily more useful. The index is created from the Plover 
dictionary, which is very large (about 150,000 translations) with many useless and even erroneous entries. As the 
index grows, so does the loading time, and past a certain point the garbage will start to crowd out useful information. 
There are few practical reasons to increase the index size beyond 15.</p>"""


class IndexDialog(FormDialog):
    """ Qt index dialog window object. Contains labels and a single interactive slider. """

    TITLE = "Choose Index Size"
    SIZE = (360, 320)

    sizeSlider: QSlider = None  # Horizontal slider with range 1-20 for relative index size.

    def new_layout(self) -> QLayout:
        layout = QVBoxLayout(self)
        heading_label = QLabel(self)
        heading_label.setWordWrap(True)
        heading_label.setText(_HEADING_TEXT)
        self.sizeSlider = QSlider(self)
        self.sizeSlider.setMinimum(1)
        self.sizeSlider.setMaximum(20)
        self.sizeSlider.setValue(12)
        self.sizeSlider.setOrientation(Qt.Horizontal)
        self.sizeSlider.setTickPosition(QSlider.TicksBelow)
        self.sizeSlider.setTickInterval(1)
        self.sizeSlider.valueChanged.connect(self.new_slider_value)
        desc_label = QLabel(self)
        desc_label.setWordWrap(True)
        desc_label.setText(_BODY_TEXT)
        layout.addWidget(heading_label)
        layout.addWidget(self.sizeSlider)
        layout.addWidget(desc_label)
        return layout

    def submit(self) -> int:
        """ Return the size to the index creation component. """
        return self.sizeSlider.value()

    # Slots
    def new_slider_value(self, value:int) -> None:
        """ Show a tooltip with the current numerical value when the slider is moved. """
        QToolTip.showText(self.pos() + self.sizeSlider.pos(), str(value), self.sizeSlider)
