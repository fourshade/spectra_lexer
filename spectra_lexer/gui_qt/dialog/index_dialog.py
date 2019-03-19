from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QSlider, QVBoxLayout, QWidget, QToolTip

from .gui_dialog import Dialog

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


class IndexDialog(Dialog):
    """ Qt index dialog window object. Contains relatively few elements. """

    def __init__(self, parent:QWidget, submit_cb:Callable):
        super().__init__(parent, submit_cb, "Choose Index Size", 360, 320)
        layout_main = QVBoxLayout(self)
        heading_label = QLabel(self)
        heading_label.setWordWrap(True)
        heading_label.setText(_HEADING_TEXT)
        layout_main.addWidget(heading_label)
        self.sizeSlider = QSlider(self)
        self.sizeSlider.setMinimum(1)
        self.sizeSlider.setMaximum(20)
        self.sizeSlider.setValue(12)
        self.sizeSlider.setOrientation(Qt.Horizontal)
        self.sizeSlider.setTickPosition(QSlider.TicksBelow)
        self.sizeSlider.setTickInterval(1)
        self.sizeSlider.valueChanged.connect(self.new_slider_value)
        layout_main.addWidget(self.sizeSlider, 0, Qt.AlignVCenter)
        desc_label = QLabel(self)
        desc_label.setWordWrap(True)
        desc_label.setText(_BODY_TEXT)
        layout_main.addWidget(desc_label)
        layout_main.addWidget(self.make_buttons())

    def submit(self) -> int:
        """ Return the size to the index creation component. """
        return self.sizeSlider.value()

    def new_slider_value(self, value:int) -> None:
        """ Show a tooltip with the current numerical value when the slider is moved. """
        QToolTip.showText(self.pos() + self.sizeSlider.pos(), str(value), self.sizeSlider)
