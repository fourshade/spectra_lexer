from spectra_lexer import Component

_ACCEPT_LABEL = "OK"
_REJECT_LABEL = "Cancel"

_STARTUP_MESSAGE = """
<p>In order to cross-reference examples of specific steno rules, this program must create an index
using your Plover dictionary. The default file size is around 10 MB, and can take anywhere
between 5 seconds and 5 minutes depending on the speed of your machine and hard disk. Would you
like to create one now? You will not be asked again.</p>
<p>(If you cancel, all other features will still work. You can always create the index later from
the Tools menu, and can expand it from the default size as well if it is not sufficient).</p>"""

_SIZE_UPPER_TEXT = """
<p>Please choose the size for the new index. The relative size factor is a number between 1 and 20:</p>
<p>size = 1: includes nothing.</p>
<p>size = 10: fast index with relatively simple words.</p>
<p>size = 12: average-sized index (default).</p>
<p>size = 15: slower index with more advanced words.</p>
<p>size = 20: includes everything.</p>"""

_SIZE_LOWER_TEXT = """
<p align="justify">An extremely large index is not necessarily more useful. The index is created from the Plover 
dictionary, which is very large (about 150,000 translations) with many useless and even erroneous entries. As the 
index grows, so does the loading time, and past a certain point the garbage will start to crowd out useful information. 
There are few practical reasons to increase the index size beyond 15.</p>"""

MINIMUM_SIZE = 1
DEFAULT_SIZE = 12
MAXIMUM_SIZE = 20


class IndexTool(Component):
    """ Controls user-based index creation. """

    index_menu = resource("menu:Tools:Make Index...", ["index_tool_open"])
    translations = resource("translations", {})

    @on("index_tool_open")
    def open(self) -> None:
        """ Create the dialog. If the index size was positive, the dialog was accepted, so create the custom index. """
        size_range = (MINIMUM_SIZE, DEFAULT_SIZE, MAXIMUM_SIZE)
        self.get_index_size(self.size_submit, _SIZE_UPPER_TEXT, _SIZE_LOWER_TEXT, size_range)

    def get_index_size(self, callback, upper_text:str, lower_text:str, size_range:tuple) -> None:
        """ Open a dialog for the index size slider that submits a positive number on accept, or 0 on cancel. """
        raise NotImplementedError

    def size_submit(self, index_size:int) -> None:
        """ If the index size was positive, the dialog was accepted, so create the custom index. """
        if index_size:
            self._send_index_commands(index_size)

    @on("index_not_found", pipe_to="new_index")
    def startup_dialog(self) -> dict:
        """ If there is no index file (first start), present a dialog for the user to make a default-sized index.
            Make the starting index on accept, otherwise save an empty one so the message doesn't appear again. """
        choice = self.startup_confirmation("Make Index", _STARTUP_MESSAGE, _ACCEPT_LABEL, _REJECT_LABEL)
        if choice != _ACCEPT_LABEL:
            return {}
        self._send_index_commands()

    def startup_confirmation(self, title:str, body:str, *choices:str) -> str:
        """ Open a dialog and return the user's selection as a string. """
        raise NotImplementedError

    def _send_index_commands(self, index_size:int=DEFAULT_SIZE) -> None:
        """ Set the size, run the command, and show a starting message in the title field.
            This thread will be busy, so the GUI will not respond to user interaction. Disable it. """
        self.engine_call("gui_set_enabled", False)
        self.engine_call("new_status", "Making new index...")
        self.engine_call("lexer_make_index", self.translations, size=index_size)

    @on("new_index", pipe_to="index_save")
    def index_finished(self, d:dict) -> dict:
        """ Once the new index has been received, we can load it, send the success message, and re-enable the GUI. """
        self.engine_call("res:index", d)
        self.engine_call("new_status", "Successfully created index!" if d else "Skipped index creation.")
        self.engine_call("gui_set_enabled", True)
        return d
