from typing import Iterable

from spectra_lexer.core import Component
from spectra_lexer.file import CFG, FileHandler, JSON


class FileTool(Component):
    """ Controls user-based file loading and window closing. """

    m_rules = resource("menu:File:Load System...",       ["file_tool_open", "system", CFG])
    m_trans = resource("menu:File:Load Translations...", ["file_tool_open", "translations", JSON])
    m_index = resource("menu:File:Load Index...",        ["file_tool_open", "index", JSON])
    m_sep = resource("menu:File:SEP",                    [])
    m_window = resource("menu:File:Close",               ["gui_window_close"])

    @on("file_tool_open")
    def open(self, res_type:str, handler:FileHandler) -> None:
        """ Present a dialog for the user to select files of a specific resource type. """
        filename = self.get_filename(f"Load {res_type.title()}", "Supported files", handler.extensions())
        # Attempt to load the selected file (if any).
        if filename:
            self.engine_call(f"{res_type}_load", filename)
            self.engine_call("new_status", f"Loaded {res_type} from file dialog.")

    def get_filename(self, title:str, fmts_msg:str, fmts:Iterable[str]) -> str:
        raise NotImplementedError
