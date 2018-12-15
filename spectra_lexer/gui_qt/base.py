from functools import partial

from spectra_lexer import SpectraComponent


class GUIQtComponent(SpectraComponent):
    """ Subclass for any GUI component that sends and receives commands from the Spectra engine.
        These components are expected to live only as long as the main window does. """

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks.
            Some commands have identical signatures to the Qt GUI methods; those can be passed directly. """
        return {**super().engine_commands(),
                "new_window": self.on_new_window}

    def engine_slots(self) -> dict:
        """ Components provide a dict with the Qt signals they accept here. By default, they accept nothing.
            Each subclass should add the components from its super call to the ones it returns. """
        return {}

    def on_new_window(self) -> None:
        """ Route all Qt signals to their corresponding engine signals (or other methods) once the engine is ready. """
        for (slot, cmd) in self.engine_slots().items():
            slot.connect(partial(self.engine_call, cmd))
