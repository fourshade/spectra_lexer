from .dialog import MessageDialog, SliderDialog
from spectra_lexer.gui import IndexTool


class IndexDialog(SliderDialog):
    """ Qt dialog window object with labels and a single interactive slider. """

    TITLE = "Choose Index Size"
    SIZE = (360, 320)


class GUIQtIndexTool(IndexTool):
    """ Controls user-based index creation. """

    window = resource("gui:window", desc="Main window object. Must be the parent of any new dialogs.")

    def get_index_size(self, *args) -> None:
        """ Open a dialog for the index size slider that submits a positive number on accept, or 0 on cancel. """
        IndexDialog(self.window, *args).show()

    def startup_confirmation(self, title:str, body:str, *choices:str) -> str:
        """ Create a simple modal message dialog and return the user's selection from <choices> as a string.
            Send the rightmost choice if the dialog was closed another way. """
        return MessageDialog(self.window, title, body, *choices)
