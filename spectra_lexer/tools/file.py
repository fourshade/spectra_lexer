from spectra_lexer import Component
from spectra_lexer.file import CFG, FileHandler, JSON


class FileTool(Component):
    """ Controls user-based file loading and window closing. """

    m_rules = resource("menu:File:Load System...",       ["file_tool_open", "system", CFG])
    m_trans = resource("menu:File:Load Translations...", ["file_tool_open", "translations", JSON])
    m_index = resource("menu:File:Load Index...",        ["file_tool_open", "index", JSON])
    m_sep = resource("menu:File:SEP",                    [])
    m_window = resource("menu:File:Close",               ["gui_window_close"])

    _last_type: str = ""  # Last resource type with a dialog load attempt.

    @on("file_tool_open", pipe_to="new_dialog")
    def open(self, res_type:str, handler:FileHandler) -> tuple:
        """ Present a dialog for the user to select files of a specific resource type. """
        self._last_type = res_type
        return "file", ["file_tool_send"], f"Load {res_type.title()}", "Supported files", handler.extensions()

    @on("file_tool_send")
    def send(self, filename:str) -> None:
        # Attempt to load the selected file (if any).
        if filename:
            self.engine_call(f"{self._last_type}_load", filename)
            self.engine_call("new_status", f"Loaded {self._last_type} from file dialog.")
