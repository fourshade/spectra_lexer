""" Base module for the GUI Qt package. Includes utility functions common to GUI operations. """

from functools import partial

from spectra_lexer import on, SpectraComponent


class GUIQtSignalComponent(SpectraComponent):

    # By default, components have no signals to connect. This can be overridden in __init__()
    signal_dict: dict = {}

    @on("configure")
    def connect_signals(self, *args, connect_fn=None, **kwargs) -> None:
        """ Connect a dict of signals from the GUI to commands through the engine.
            This is required in order for the engine to catch exceptions from this code.
            The command methods must already have been decorated with their key. """
        for signal, cmd_key in self.signal_dict.items():
            call_fn = partial(self.engine_send, cmd_key)
            if connect_fn is None:
                # Default behavior is based on pyqtSignal.connect().
                signal.connect(call_fn)
            else:
                connect_fn(signal, call_fn)
