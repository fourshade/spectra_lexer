from spectra_lexer import Component


class Window(Component):
    """ General operations class for the main window. This component handles many app-wide events in general. """

    @on("init:menu")
    def start(self, menu:dict) -> None:
        """ Get everything we need from the window implementation and send it all to the GUI components. """
        self.engine_call("res:gui:", self.get_window_elements())
        # Load the menu first specifically, since it has its own options.
        self.engine_call("load_menu", menu)
        # Let components know the options are done so they can start loading the rest of the GUI.
        self.engine_call("load_gui")
        # Even once the window is visible, the user shouldn't interact with it until files are done loading.
        self.engine_call("new_status", "Loading...")
        self.engine_call("gui_set_enabled", False)
        self.show()

    def get_window_elements(self) -> dict:
        """ Get all required elements from the window to send to other GUI components. """
        raise NotImplementedError

    @on("gui_window_show")
    def show(self) -> None:
        """ This must be called on start, and also to re-open a plugin window for its host application. """
        raise NotImplementedError

    @on("gui_window_close")
    def close(self) -> None:
        """ Closing the main window kills the program in standalone mode, but not as a plugin. """
        raise NotImplementedError

    @on("resources_done")
    def enable(self) -> None:
        """ All files have command line options, so when this command is issued, everything must be done. """
        self.engine_call("gui_set_enabled", True)
        self.engine_call("new_status", "Loading complete.")