from spectra_lexer import Component

_ACCEPT_LABEL = "OK"
_REJECT_LABEL = "Cancel"
_STARTUP_MESSAGE = "In order to cross-reference examples of specific steno rules, this program must create an index " \
                   "using your Plover dictionary. The default size is around 10 MB, and can take anywhere between 5 " \
                   "seconds and 5 minutes depending on the speed of your machine and hard disk. Would you like to " \
                   "create one now? You will not be asked again.\n\n" \
                   "(If you cancel, all other features will still work. You can always create the index later from " \
                   "the Tools menu, and can expand it from the default size as well if it is not sufficient)."


class IndexDialogTool(Component):
    """ Controls user-based index creation. """

    make_index = Option("menu", "Tools:Make Index...", ["new_dialog", "index"])

    @on("index_dialog_result")
    def new_custom(self, index_size:int) -> None:
        """ If the index size was positive, the dialog was accepted, so create the custom index. """
        if index_size:
            self._send_index_commands(index_size)

    @on("index_not_found", "new_dialog")
    def startup_dialog(self) -> tuple:
        """ If there is no index file (first start), present a dialog for the user to make a default-sized index. """
        title = "Make Index"
        msg = _STARTUP_MESSAGE
        return "index-message", title, msg, _ACCEPT_LABEL, _REJECT_LABEL

    @on("message_dialog_result")
    def new_default(self, owner:str, choice:str) -> None:
        """ Make the starting index on accept, otherwise save an empty one so the message doesn't appear again. """
        if owner == "index" and choice == _ACCEPT_LABEL:
            self._send_index_commands()
        else:
            self.engine_call("index_save", {})

    def _send_index_commands(self, index_size:int=None) -> None:
        """ When creating the index, the lexer should only keep results with all keys matched to reduce garbage.
            Set the size, run the command, and show starting and finishing messages in the title field. """
        self.engine_call("new_status", "Making new index...")
        self.engine_call(f"set_config_lexer:need_all_keys", True)
        index = self.engine_call("index_generate", size=index_size)
        self.engine_call("index_save", index)
        self.engine_call("new_status", "Successfully created index!")
