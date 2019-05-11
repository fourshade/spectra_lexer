from spectra_lexer.core import Component


class Window(Component):
    """ General operations class for the main window. This component handles many app-wide events in general. """

    @on("gui_load")
    def load(self) -> None:
        # Even once the window is visible, the user shouldn't interact with it until files are done loading.
        self.engine_call("new_status", "Loading...")
        self.engine_call("gui_set_enabled", False)
        self.show()

    @on("gui_window_show")
    def show(self) -> None:
        """ This is always called on start, and for a plugin window, by its host application to re-open it. """
        raise NotImplementedError

    @on("gui_window_close")
    def close(self) -> None:
        """ Closing the main window should kill the program in standalone mode, but not as a plugin. """
        raise NotImplementedError

    @on_resource("translations")
    def enable(self, *args) -> None:
        """ Translations are the last large file I/O task to complete before the GUI is usable. """
        self.engine_call("gui_set_enabled", True)
        self.engine_call("new_status", "Loading complete.")
