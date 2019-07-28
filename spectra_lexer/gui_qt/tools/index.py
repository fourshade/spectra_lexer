from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QLayout, QMessageBox, QSlider, QToolTip, QVBoxLayout, QWidget

from .dialog import FormDialog
from spectra_lexer.resource import StenoIndex

STARTUP_MESSAGE = """
<p>In order to cross-reference examples of specific steno rules, this program must create an index
using your Plover dictionary. The default file size is around 10 MB, and can take anywhere
between 5 seconds and 5 minutes depending on the speed of your machine and hard disk. Would you
like to create one now? You will not be asked again.</p>
<p>(If you cancel, all other features will still work. You can always create the index later from
the Tools menu, and can expand it from the default size as well if it is not sufficient).</p>"""


def default_index_dialog(parent:QWidget) -> int:
    """ Present a dialog for the user to make a default-sized index. Return that size on accept, or 0 on cancel. """
    yes, no = QMessageBox.Yes, QMessageBox.No
    button = QMessageBox.question(parent, "Make Index", STARTUP_MESSAGE, yes | no)
    return (button == yes) * StenoIndex.DEFAULT_SIZE


TEXT_ABOVE_SLIDER = f"""
<p>Please choose the size for the new index. The relative size factor is a number between 1 and 20:</p>
<p>{'</p><p>'.join(StenoIndex.SIZE_DESCRIPTIONS)}</p>"""

TEXT_BELOW_SLIDER = """
<p align="justify">An extremely large index is not necessarily more useful. The index is created from the Plover 
dictionary, which is very large (about 150,000 translations) with many useless and even erroneous entries. As the 
index grows, so does the loading time, and past a certain point the garbage will start to crowd out useful information. 
Unless you are doing batch analysis, there is little benefit to a maximum-sized index.</p>"""


class SliderIndexDialog(FormDialog):
    """ Qt dialog window with an interactive slider that submits a positive number on accept, or 0 on cancel. """

    TITLE = "Choose Index Size"
    SIZE = (360, 320)

    slider: QSlider = None  # Horizontal slider.

    def new_layout(self) -> QLayout:
        layout = QVBoxLayout(self)
        heading_label = QLabel(self)
        heading_label.setWordWrap(True)
        heading_label.setText(TEXT_ABOVE_SLIDER)
        self.slider = QSlider(self)
        self.slider.setMinimum(StenoIndex.MINIMUM_SIZE)
        self.slider.setMaximum(StenoIndex.MAXIMUM_SIZE)
        self.slider.setValue(StenoIndex.DEFAULT_SIZE)
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self.new_slider_value)
        desc_label = QLabel(self)
        desc_label.setWordWrap(True)
        desc_label.setText(TEXT_BELOW_SLIDER)
        layout.addWidget(heading_label)
        layout.addWidget(self.slider)
        layout.addWidget(desc_label)
        return layout

    def submit(self) -> int:
        """ Return the slider position on submit. """
        return self.slider.value()

    # Slots
    def new_slider_value(self, value:int) -> None:
        """ Show a tooltip with the current numerical value when the slider is moved. """
        QToolTip.showText(self.pos() + self.slider.pos(), str(value), self.slider)
