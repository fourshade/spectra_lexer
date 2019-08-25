""" Main entry point for Spectra's interactive GUI application. """

import sys
from traceback import format_exception

from PyQt5.QtWidgets import QApplication

from .dialog import QtDialogLayer
from .dispatch import AsyncThreadLoader
from .plover import PloverInterface, PloverProxy
from .window import WindowController
from spectra_lexer import Spectra
from spectra_lexer.app import StenoApplication, StenoOptions


class QtGUIController:
    """ Master component for GUI Qt operations. Controls the application as a whole. """

    window: WindowController
    threader: AsyncThreadLoader
    dialogs: QtDialogLayer
    app: StenoApplication = None
    last_exception: Exception = None

    def __init__(self, *args) -> None:
        """ Load the user layer asynchronously on a new thread to avoid blocking the GUI. """
        window = self.window = WindowController()
        threader = self.threader = AsyncThreadLoader(window.set_enabled, window.set_status, self.handle_exception)
        self.dialogs = QtDialogLayer(window, threader)
        threader.run(StenoApplication, *args, callback=self.connect)
        window.show()

    def connect(self, app:StenoApplication) -> None:
        """ Once the user layer is loaded, it is safe to connect GUI components to it. """
        self.app = app
        self.window.connect(app.process_action, self.threader.protect)
        # Provide all instance attributes for use in a console or debug context.
        self.dialogs.connect(app, vars(self))

    def handle_exception(self, exc:Exception, max_frames:int=10) -> None:
        """ Format, log, and display a stack trace. Save the exception for introspection. """
        self.last_exception = exc
        tb_text = "".join(format_exception(type(exc), exc, exc.__traceback__, limit=max_frames))
        app = self.app
        if app is None:
            tb_text += "\nAPP SETUP FAILED - COULD NOT LOG EXCEPTION.\n"
        else:
            app.log('EXCEPTION\n' + tb_text)
        self.window.show_traceback(tb_text)

    @classmethod
    def with_loop(cls, *args) -> int:
        """ Create a QApplication and load the GUI in standalone mode. """
        qt_app = QApplication(sys.argv)
        # The main object must be assigned to a dummy local, or else Qt will garbage-collect it and crash...
        _ = cls(*args)
        # After everything is loaded, start a GUI event loop and run it indefinitely.
        return qt_app.exec_()


# Standalone GUI Qt application entry point.
gui = Spectra(QtGUIController.with_loop, StenoOptions)


class PloverQtGUIController(QtGUIController):
    """ GUI subclass adding Plover interface components. """

    plover: PloverInterface

    def __init__(self, engine, *args) -> None:
        """ For a plugin window, self.show() is called by its host application to re-open it after closing.
            self.close() should kill the program in standalone mode, but not as a plugin. """
        super().__init__(*args)
        window = self.window
        self.show = window.show
        self.close = window.close
        self.plover = PloverInterface(window, engine)

    def connect(self, app:StenoApplication) -> None:
        super().connect(app)
        self.plover.connect(app)


class plover(PloverProxy):
    """ Main entry point for Spectra's Plover plugin application. Called with the Plover engine as the only argument.
        We must not create our own QApplication object or run our own event loop if Plover is running. """

    def __init__(self, engine) -> None:
        """ Create the main application, but do not directly expose it. This proxy will be returned instead.
            We get translations from the Plover engine, so auto-loading from disk must be suppressed. """
        opts = StenoOptions()
        opts.translations_files = []
        self.app = PloverQtGUIController(engine, opts)
