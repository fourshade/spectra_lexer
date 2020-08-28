from typing import Callable

from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import QDialog, QLabel, QWidget

from .index_dialog_ui import Ui_IndexSizeDialog

SizeCallback = Callable[[int], None]
WINDOW_FLAGS = Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint


class SliderInfo(QObject):
    """ Updates an info label to correspond to a slider's numerical value. """

    def __init__(self, parent:QLabel) -> None:
        super().__init__(parent)
        self._info = {}

    def add(self, value:int, text:str) -> None:
        """ Map a slider value to <text>. """
        self._info[value] = text

    def add_range(self, start:int, end:int, text:str) -> None:
        """ Map each slider value in the range [start, end) to <text>. """
        for i in range(start, end):
            self._info[i] = text

    def update(self, value:int) -> None:
        text = self._info.get(value)
        if text is not None:
            self.parent().setText(text)


def index_size_dialog(parent:QWidget=None, *, min_size=0, max_size=20,
                      default_size:int=None, on_accept:SizeCallback=None) -> QDialog:
    """ Open a Qt dialog tool with an interactive slider that submits an index size on accept. """
    dialog = QDialog(parent, WINDOW_FLAGS)
    ui = Ui_IndexSizeDialog()
    ui.setupUi(dialog)
    ui.w_minsize.setText(str(min_size))
    ui.w_maxsize.setText(str(max_size))
    if default_size is None:
        default_size = (min_size + max_size) // 2
    # Add info for all index sizes from smallest to largest.
    info = SliderInfo(ui.w_info)
    info.add(min_size, 'No index (fastest)')
    info.add_range(min_size + 1, default_size, 'Smaller index (faster)')
    info.add(default_size, 'Average size (default)')
    info.add_range(default_size + 1, max_size, 'Larger index (slower)')
    info.add(max_size, 'Complete index (slowest)')
    w_slider = ui.w_slider
    w_slider.valueChanged.connect(info.update)
    w_slider.setMinimum(min_size)
    w_slider.setMaximum(max_size)
    w_slider.setValue(default_size)
    # Send the slider position to the callback on accept.
    if on_accept is not None:
        dialog.accepted.connect(lambda: on_accept(w_slider.value()))
    return dialog
