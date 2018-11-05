from PyQt5.QtWidgets import QDialog

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

    _plugin_layer: PloverPluginLayer  # Delegate practically everything to the plugin layer.

    def __init__(self, *args):
        # TODO: save the window state when closed?
        super().__init__()
        self.setupUi(self)
        # Only two things of interest can happen: we can get a new set of dictionaries,
        # or a new set of translations. Either will be handled by the plugin layer and
        # the results dispatched to the child widget through callbacks.
        self._plugin_layer = PloverPluginLayer(*args,
                                               dict_callback=self.w_main.set_dictionary,
                                               out_callback=self.w_main.query)
