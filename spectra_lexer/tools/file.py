from typing import Sequence

from spectra_lexer import Component


class FileDialogTool(Component):
    """ Controls user-based file loading and window closing. """

    load_rules = Resource("menu", "File:Load Rules...", ["file_dialog_open", "rules"])
    load_translations = Resource("menu", "File:Load Translations...", ["file_dialog_open", "translations"])
    load_index = Resource("menu", "File:Load Index...", ["file_dialog_open", "index"])
    sep = Resource("menu", "File:")
    close_window = Resource("menu", "File:Close", ["gui_window_close"])

    @on("file_dialog_open", pipe_to="new_dialog")
    def open_dialog(self, res_type:str) -> tuple:
        """ Present a dialog for the user to select files of a specific resource type. """
        title_msg = f"Load {res_type.title()}"
        # Currently only JSON-type files are supported for loading.
        fmts_msg = "JSON files"
        fmts = ".json", ".cson"
        return f"{res_type}-file", title_msg, fmts_msg, fmts

    @on("file_dialog_result")
    def load(self, res_type:str, filenames:Sequence[str]=()) -> None:
        """ Attempt to load the given files (if any). """
        if filenames:
            self.engine_call("new_status", f"Loading {res_type}...")
            self.engine_call(f"{res_type}_load", filenames)
            self.engine_call("new_status", f"Loaded {res_type} from file dialog.")
