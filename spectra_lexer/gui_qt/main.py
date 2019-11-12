""" Main entry point for Spectra's interactive GUI application. """

import sys
from traceback import format_exception
from typing import Callable

from PyQt5.QtWidgets import QApplication

from .gui import QtGUI, QtGUIFactory
from .system import QtAsyncDispatcher, QtExceptionTrap
from spectra_lexer.app import StenoApplication
from spectra_lexer.base import StenoAppFactory, StenoAppOptions
from spectra_lexer.log import StreamLogger


class QtGUIExtension:

    def __init__(self, logger:StreamLogger, exc_trap:QtExceptionTrap, gui:QtGUI) -> None:
        self._logger = logger
        self._gui = gui
        self._exc_trap = exc_trap
        self._async_dsp = QtAsyncDispatcher(exc_trap)


class QtGUIController:
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: Exception = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, logger:StreamLogger, exc_trap:QtExceptionTrap, gui:QtGUI) -> None:
        self._logger = logger
        self._exc_trap = exc_trap
        self._async_dsp = QtAsyncDispatcher(exc_trap)
        self._gui = gui
        self._app = None

    def connect(self, app:StenoApplication) -> None:
        """ On first start, present a dialog for the user to make a default-sized index on accept. """
        self._app = app
        # Connect all GUI input signals to the action function.
        self._gui.connect(self._action)
        if app.is_first_run:
            if self._gui.confirm_startup_index():
                self._make_index()

    def _action(self, action:str) -> None:
        """ Send an action command with the current state.
            Run through the returned changes and update the GUI state with any relevant ones. """
        if self._app is not None:
            with self._exc_trap:
                state = self._gui.get_state()
                changed = self._app.process_action(state, action)
                self._gui.set_state(**changed)

    def open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self._gui.select_translations_files()
        if filenames:
            self._run_async(self._app.load_translations, *filenames, msg_done="Loaded translations from file dialog.")

    def open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self._gui.select_index_file()
        if filename:
            self._run_async(self._app.load_index, filename, msg_done="Loaded index from file dialog.")

    def config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        info = self._app.get_config_info()
        self._gui.open_config_editor(self._update_config, info)

    def _update_config(self, options:dict) -> None:
        self._run_async(self._app.set_config, options, msg_done="Configuration saved.")

    def custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        self._gui.open_index_creator(self._make_index)

    def _make_index(self, size:int=None) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self._gui.set_status("Making new index...")
        self._run_async(self._app.make_index, size, msg_done="Successfully created index!")

    def debug_console(self) -> None:
        """ Create and show the debug console dialog. """
        self._gui.open_debug_console(self._debug_vars())

    def debug_tree(self) -> None:
        """ Create and show the debug tree dialog. """
        self._gui.open_debug_tree(self._debug_vars())

    def _debug_vars(self) -> dict:
        return vars(self).copy()

    def _run_async(self, func:Callable, *args, msg_done:str=None) -> None:
        """ Disable the window controls in order to start a blocking async task.
            Make a callback that will re-enable the controls and optionally show <msg_done> when the task is done. """
        self._gui.disable()
        def on_task_finish(ret_val) -> None:
            self._gui.enable(msg_done)
        self._async_dsp.dispatch(func, *args, callback=on_task_finish)

    def handle_exception(self, exc:Exception, max_frames=20) -> None:
        """ Format, log, and display a stack trace for any thrown exception.
            Store the exception and enable all widgets afterward to allow debugging. """
        self.last_exception = exc
        tb_text = "".join(format_exception(type(exc), exc, exc.__traceback__, limit=max_frames))
        self._logger.log('EXCEPTION\n' + tb_text)
        self._gui.show_traceback(tb_text)


class QtAppFactory(StenoAppFactory):
    """ Main factory for the Qt GUI application. """

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._gui = QtGUIFactory().build()

    def build(self) -> None:
        """ Build all components necessary to operate the GUI. """
        gui = self._gui
        logger = self.build_logger()
        exc_trap = QtExceptionTrap()
        controller = self._controller = QtGUIController(logger, exc_trap, gui)
        exc_trap.connect(controller.handle_exception)
        # Connect all dialog menu items through the exception trap.
        wrap = exc_trap.wrap
        gui.menu_add(wrap(controller.open_translations), "File", "Load Translations...")
        gui.menu_add(wrap(controller.open_index), "File", "Load Index...")
        gui.menu_add(wrap(gui.close), "File", "Close", after_sep=True)
        gui.menu_add(wrap(controller.config_editor), "Tools", "Edit Configuration...")
        gui.menu_add(wrap(controller.custom_index), "Tools", "Make Index...")
        gui.menu_add(wrap(controller.debug_console), "Debug", "Open Console...")
        gui.menu_add(wrap(controller.debug_tree), "Debug", "View Object Tree...")
        gui.disable("Loading...")
        gui.show()
        # Build the app object asynchronously on a new thread to avoid blocking the GUI.
        self.async_dsp = QtAsyncDispatcher(exc_trap)
        self.async_dsp.dispatch(self.build_app, callback=self.connect)

    def connect(self, app:StenoApplication) -> None:
        """ Once the app object is loaded, it is safe to connect GUI extensions. """
        self._controller.connect(app)
        self._gui.enable("Loading complete.")


def main() -> int:
    """ Create a QApplication and load the GUI in standalone mode. """
    qt_app = QApplication(sys.argv)
    options = StenoAppOptions(__doc__)
    options.parse()
    factory = QtAppFactory(options)
    # The returned object must be assigned to a dummy local, or else Qt will garbage-collect it and crash...
    factory.build()
    # After everything is loaded, start a GUI event loop and run it indefinitely.
    return qt_app.exec_()


if __name__ == '__main__':
    sys.exit(main())
