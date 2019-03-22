from .main_window import MainWindow
from spectra_lexer import Component


class GUIQtWindow(Component):
    """ GUI Qt operations class for the main window. This component handles many app-wide events in general. """

    window: MainWindow = None  # Main GUI window. All GUI activity (including dialogs) is coupled to this window.

    @on("gui_start")
    def gui_start(self, **options) -> None:
        """ Make the window, get all required widgets from it, and send those to the components. """
        self.window = MainWindow()
        for key, val in self.window.widgets().items():
            self.engine_call(f"set_gui_{key}", val)
        self.engine_call("gui_opts_done")
        # Even once the window is done, the user shouldn't interact with it until files are done loading.
        self.engine_call("new_status", "Loading...")
        self.engine_call("gui_set_enabled", False)

    @on("gui_window_show")
    def show(self) -> None:
        """ This must be called on start, and also to re-open a plugin window for its host application. """
        if self.window is not None:
            self.window.show()
            self.window.activateWindow()
            self.window.raise_()

    @on("gui_window_close")
    def close(self) -> None:
        """ Closing the main window kills the program in standalone mode, but not as a plugin. """
        if self.window is not None:
            self.window.close()

    @on("cmdline_thread_done")
    def enable(self):
        """ All files have command line options, so when this command is issued, everything must be done. """
        self.engine_call("gui_set_enabled", True)
        self.engine_call("new_status", "Loading complete.")
