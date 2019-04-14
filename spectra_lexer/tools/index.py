from spectra_lexer import Component

_ACCEPT_LABEL = "OK"
_REJECT_LABEL = "Cancel"
_STARTUP_MESSAGE = "In order to cross-reference examples of specific steno rules, this program must create an index " \
                   "using your Plover dictionary. The default file size is around 10 MB, and can take anywhere " \
                   "between 5 seconds and 5 minutes depending on the speed of your machine and hard disk. Would you " \
                   "like to create one now? You will not be asked again.\n\n" \
                   "(If you cancel, all other features will still work. You can always create the index later from " \
                   "the Tools menu, and can expand it from the default size as well if it is not sufficient)."


class IndexTool(Component):
    """ Controls user-based index creation. """

    # Create and show index size choice dialog.
    index_menu = Resource("menu", "Tools:Make Index...", ["new_dialog", "index", ["index_tool_size_send"]])
    translations = Resource("dict", "translations", {})  # Translations dict for mass queries.

    @on("index_tool_size_send")
    def size_submit(self, index_size:int) -> None:
        """ If the index size was positive, the dialog was accepted, so create the custom index. """
        if index_size:
            self._send_index_commands(index_size)

    @on("index_not_found", pipe_to="new_dialog")
    def startup_dialog(self) -> tuple:
        """ If there is no index file (first start), present a dialog for the user to make a default-sized index. """
        return "message_index", ["index_tool_start_send"], "Make Index", _STARTUP_MESSAGE, _ACCEPT_LABEL, _REJECT_LABEL

    @on("index_tool_start_send")
    def startup_result(self, choice:str) -> None:
        """ Make the starting index on accept, otherwise save an empty one so the message doesn't appear again. """
        if choice == _ACCEPT_LABEL:
            self._send_index_commands()
        else:
            self.engine_call("new_index", {})

    def _send_index_commands(self, index_size:int=None) -> None:
        """ Set the size, run the command, and show a starting message in the title field.
            This thread will be busy, so the GUI will not respond to user interaction. Disable it. """
        self.engine_call("gui_set_enabled", False)
        self.engine_call("new_status", "Making new index...")
        self.engine_call("lexer_make_index", self.translations, size=index_size)

    @on("new_index", pipe_to="index_save")
    def index_finished(self, d:dict) -> dict:
        """ Once the new index has been received, we can load it, send the success message, and re-enable the GUI. """
        self.engine_call("set_dict_index", d)
        self.engine_call("new_status", "Successfully created index!" if d else "Skipped index creation.")
        self.engine_call("gui_set_enabled", True)
        return d
