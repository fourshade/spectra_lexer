from spectra_lexer import Component


class FileDialogTool(Component):
    """ Controls user-based file loading and window closing. This should not be loaded in plugin mode. """

    load_rules = Option("menu", "File:Load Rules...", ["new_file_dialog", "rules"])
    load_translations = Option("menu", "File:Load Translations...", ["new_file_dialog", "translations"])
    sep = Option("menu", "File:SEPARATOR")
    close_window = Option("menu", "File:Exit", ["gui_window_close"])

    @on("new_file_dialog")
    def new_dialog(self, d_type:str) -> None:
        """ Present a dialog for the user to select files. Attempt to load them if not empty. """
        fmts = self.engine_call("file_get_extensions")
        title_msg = f"Load {d_type.title()}"
        filter_msg = f"Supported file formats (*{' *'.join(fmts)})"
        (filenames, _) = self.engine_call("gui_window_file_dialog", title_msg, ".", filter_msg)
        if filenames:
            self.engine_call("new_status", f"Loading {d_type}...")
            self.engine_call(d_type + "_load", filenames)
            self.engine_call("new_status", f"Loaded {d_type} from file dialog.")
