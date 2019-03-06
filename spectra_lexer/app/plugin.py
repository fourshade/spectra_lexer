from PyQt5.QtWidgets import QDialog

from spectra_lexer import core, gui_qt, interactive, plover
from spectra_lexer.app import Application


class PloverDialog(QDialog):
    """ Main entry point for the Plover plugin. Non-instantiatable dummy class with parameters required by Plover.
        The actual window returned by __new__ is the standard QMainWindow used by the standalone GUI.
        This class is just a facade, appearing as a QDialog to satisfy Plover's setup requirements. """

    # Class constants required by Plover for toolbar.
    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    # Docstring is used as tooltip on Plover GUI toolbar, so change it dynamically.
    __doc__ = "See the breakdown of words using steno rules."

    # The window and all of its contents are destroyed if it is closed with no referents.
    # The app's components are relatively expensive to create, so an app reference is kept
    # in the class dictionary and returned on every call after the first, making it a singleton.
    window = None

    def __new__(cls, engine=None, *args):
        """ Only create a new app/window instance on the first call; return the saved instance otherwise. """
        if cls.window is None:
            app = Application(gui_qt, plover, core, interactive)
            # The engine is always the first argument passed by Plover. Others are irrelevant.
            # Translations file loading must be suppressed; we get those from Plover instead.
            # In plugin mode, the GUI event loop isn't run by Spectra, so the Qt window is returned instead.
            cls.window = app.start(suppress_translations=True)
            app.call("plover_test") if engine is None else app.call("new_plover_engine", engine)
        return cls.window


# Entry point for testing the Plover plugin by running it with no engine in a standalone configuration.
if __name__ == '__main__':
    PloverDialog()
