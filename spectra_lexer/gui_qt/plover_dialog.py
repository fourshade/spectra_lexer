from PyQt5.QtWidgets import QDialog

from spectra_lexer import SpectraApplication
from spectra_lexer.gui_qt.plover_dialog_ui import Ui_PloverDialog
from spectra_lexer.plover import PloverPluginLayer


class PloverDialog(QDialog, Ui_PloverDialog):
    """ See the breakdown of words using steno rules. """

#   Dialog window for real-time Plover GUI plugin. Receives dictionaries and
#   translations from Plover and passes them on to the main GUI widget when ready.
#
#   Children:
#   w_main - MainWidget, handles all lexer tasks given a dictionary and/or steno translations from the user.

    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    _app: SpectraApplication          # Top-level application object. Must be a singleton that retains state.
    _plugin_layer: PloverPluginLayer  # Delegate practically everything to the plugin layer.

    def __init__(self, *args):
        """ Set up the application with the main GUI widget and the Plover interface.
            Only two things of interest can come from Plover: a new set of dictionaries
            or a new set of translations. Either will be handled by the plugin layer and
            the results dispatched to the GUI and/or the engine through the application. """
        super().__init__()
        self.setupUi(self)
        self._plugin_layer = PloverPluginLayer(*args)
        self._app = SpectraApplication(self.w_main, self._plugin_layer)
