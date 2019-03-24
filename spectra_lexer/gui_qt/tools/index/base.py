from .index_dialog import IndexDialog
from spectra_lexer import Component
from spectra_lexer.gui_qt.tools.dialog import MessageDialog

_ACCEPT_LABEL = "OK"
_REJECT_LABEL = "Cancel"
_STARTUP_MESSAGE = "In order to cross-reference examples of specific steno rules, this program must create an index " \
                   "using your Plover dictionary. The default file size is around 10 MB, and can take anywhere " \
                   "between 5 seconds and 5 minutes depending on the speed of your machine and hard disk. Would you " \
                   "like to create one now? You will not be asked again.\n\n" \
                   "(If you cancel, all other features will still work. You can always create the index later from " \
                   "the Tools menu, and can expand it from the default size as well if it is not sufficient)."


class IndexDialogTool(Component):
    """ Controls user-based index creation. """

    index_menu = Resource("menu", "Tools:Make Index...", ["index_dialog_open"])
    window = Resource("gui", "window", None, "Main window object. Must be the parent of any new dialogs.")

    @on("index_dialog_open")
    def size_dialog(self) -> None:
        """ Create and show index size choice dialog. """
        IndexDialog(self.window, self.size_submit).show()

    def size_submit(self, index_size:int) -> None:
        """ If the index size was positive, the dialog was accepted, so create the custom index. """
        if index_size:
            self._send_index_commands(index_size)

    @on("index_not_found")
    def startup_dialog(self) -> None:
        """ If there is no index file (first start), present a dialog for the user to make a default-sized index. """
        choice = MessageDialog(self.window, "Make Index", _STARTUP_MESSAGE, _ACCEPT_LABEL, _REJECT_LABEL)
        # Make the starting index on accept, otherwise save an empty one so the message doesn't appear again.
        if choice == _ACCEPT_LABEL:
            self._send_index_commands()
        else:
            self.engine_call("index_save", {})

    def _send_index_commands(self, index_size:int=None) -> None:
        """ Set the size, run the command, and show a starting message in the title field.
            This thread will be busy, so the GUI will not respond to user interaction. Disable it. """
        self.engine_call("gui_set_enabled", False)
        self.engine_call("new_status", "Making new index...")
        self.engine_call("index_generate", size=index_size, save=True)

    @on("index_save")
    def index_finished(self, d:dict, *args) -> None:
        """ Once the save command has been received, we can send the success message and re-enable the GUI. """
        self.engine_call("new_status", "Successfully created index!" if d else "Skipped index creation.")
        self.engine_call("gui_set_enabled", True)
