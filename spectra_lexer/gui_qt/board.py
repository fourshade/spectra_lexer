from .base import GUIQT


class QtBoard(GUIQT):
    """ Draws steno board diagram elements and the description for rules. """

    def GUIQTConnect(self) -> None:
        """ Connect the signals and initialize the board size. """
        self.W_BOARD.onResize.connect(self.board_resize)
        self.W_BOARD.resizeEvent()

    def VIEWNewCaption(self, caption:str) -> None:
        """ Show a caption above the board. """
        self.W_DESC.setText(caption)

    def VIEWNewBoard(self, xml_data:bytes) -> None:
        """ Send the raw XML data to the board widget. """
        self.W_BOARD.set_board(xml_data)
