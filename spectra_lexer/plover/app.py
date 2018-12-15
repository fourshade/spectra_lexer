from spectra_lexer.gui_qt.app import GUIQtAppBase
from spectra_lexer.plover.interface import PloverPluginInterface


class PloverPluginApplication(GUIQtAppBase):
    """ Top-level class for operation of the Plover plugin. """

    def __init__(self, *args, **kwargs) -> None:
        """ Initialize the application with keyword arguments from the caller. """
        super().__init__(**kwargs)
        # Plover currently initializes plugins with only positional arguments,
        # so just pass those along to the interface without looking at them.
        self.engine_send("plover_setup", *args)

    def engine_subcomponents(self) -> tuple:
        """ Default plugin support components. """
        return (*super().engine_subcomponents(), PloverPluginInterface())
