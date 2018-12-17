from spectra_lexer.gui_qt.app import GUIQtApplication
from spectra_lexer.plover.interface import PloverPluginInterface


class PloverPluginApplication(GUIQtApplication):
    """ Main application class for Plover plugin. """

    def __init__(self, *components, plover_args, **kwargs):
        super().__init__(PloverPluginInterface(*plover_args), *components, **kwargs)
