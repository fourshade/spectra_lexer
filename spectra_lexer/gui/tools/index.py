from .base import GUITool

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


class IndexTool(GUITool):
    """ Controls user-based index creation. """

    index_menu = resource("menu:Tools:Make Index...", ["index_tool_open"])

    @on("index_tool_open")
    def open(self) -> None:
        """ Create a dialog for the index size slider that submits a positive number on accept, or 0 on cancel. """
        size_range = (MINIMUM_SIZE, DEFAULT_SIZE, MAXIMUM_SIZE)
        self.open_dialog(self.size_submit, _SIZE_UPPER_TEXT, _SIZE_LOWER_TEXT, size_range)

    def size_submit(self, index_size:int) -> None:
        """ If the index size was positive, the dialog was accepted, so create the custom index. """
        if index_size:
            self._send_index_commands(index_size)

    @on("index_not_found")
    def startup_dialog(self) -> None:
        """ If there is no index file (first start), present a dialog for the user to make a default-sized index.
            Make the starting index on accept, otherwise save an empty one so the message doesn't appear again. """
        if self.confirm_new_startup_index(_STARTUP_MESSAGE):
            self._send_index_commands()
        else:
            self.engine_call("new_status", "Skipped index creation.")
            self.index_finished({})

    def confirm_new_startup_index(self, question:str) -> bool:
        """ Open a question dialog and return the user's accept/cancel decision as a bool. """
        raise NotImplementedError

    def _send_index_commands(self, index_size:int=DEFAULT_SIZE) -> None:
        """ Set the size, run the command, and show a starting message in the title field.
            It is not thread-safe for the GUI to access certain objects while processing. Disable it. """
        self.engine_call("gui_set_enabled", False)
        self.engine_call("analyzer_make_index", size=index_size)

    @on("new_index")
    def index_finished(self, d:dict) -> None:
        """ Once the new index has been received, we can save it, send the success message, and re-enable the GUI. """
        self.engine_call("index_save", d)
        self.engine_call("gui_set_enabled", True)
