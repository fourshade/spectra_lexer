""" Main entry point for Spectra's interactive GUI application. """

import sys
from traceback import format_exception
from typing import Callable, Type

from PyQt5.QtWidgets import QApplication, QMainWindow

from .system import QtAsyncDispatcher, QtExceptionTrap
from .tools import QtDialogTools
from .window import QtGUI
from spectra_lexer.app import StenoApplication
from spectra_lexer.base import StenoMain
from spectra_lexer.log import StreamLogger


class QtGUIExt:
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: Exception = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, logger:StreamLogger, async_dsp:QtAsyncDispatcher, tools:QtDialogTools,
                 gui:QtGUI, **kwargs) -> None:
        self._logger = logger
        self._async_dsp = async_dsp
        self._tools = tools
        self._gui = gui
        self._app = None

    def connect(self, app:StenoApplication) -> None:
        """ Once the app object is loaded, it is safe to connect GUI extensions.
            Connect all input signals to the function with their corresponding action and/or state attribute. """
        self._app = app
        self._gui.enable("Loading complete.")
        self._subcls_tasks()
        # If there is no index file on first start, send up a dialog.
        if app.is_first_run:
            self._startup_index()

    def _subcls_tasks(self) -> None:
        """ Perform subclass-specific setup. """
        pass

    def query(self, strokes:str, word:str) -> None:
        """ Run a lexer query on actual user strokes from a steno machine. """
        self._gui.set_state(translation=[strokes, word])
        self.action("Query", match_all_keys=False)

    def action(self, action:str, **extra_vars) -> None:
        """ Send an action command with the given state.
            Run through the returned changes and update the GUI state with any relevant ones. """
        if self._app is not None:
            state = self._gui.get_state()
            state.update(extra_vars)
            changed = self._app.process_action(state, action)
            self._gui.set_state(**changed)

    def open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self._tools.select_translations_files()
        if filenames:
            self._run_async(self._app.load_translations, *filenames, msg_done="Loaded translations from file dialog.")

    def open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self._tools.select_index_file()
        if filename:
            self._run_async(self._app.load_index, filename, msg_done="Loaded index from file dialog.")

    def config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        info = self._app.get_config_info()
        self._tools.open_config_editor(self._update_config, info)

    def _update_config(self, options:dict) -> None:
        self._run_async(self._app.set_config, options, msg_done="Configuration saved.")

    def _startup_index(self) -> None:
        """ On first start, present a dialog for the user to make a default-sized index on accept. """
        if self._tools.confirm_startup_index():
            self._make_index()

    def custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        self._tools.open_index_creator(self._make_index)

    def _make_index(self, size:int=None) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self._gui.set_status("Making new index...")
        self._run_async(self._app.make_index, size, msg_done="Successfully created index!")

    def debug_console(self) -> None:
        """ Create and show the debug console dialog. """
        self._tools.open_debug_console(self._debug_vars())

    def debug_tree(self) -> None:
        """ Create and show the debug tree dialog. """
        self._tools.open_debug_tree(self._debug_vars())

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


class QtMain(StenoMain):
    """ Main entry point and factory for the Qt GUI. """

    def build_gui(self, gui_cls:Type[QtGUIExt], **kwargs) -> QtGUI:
        """ Build all components necessary to operate the GUI. """
        logger = self.build_logger()
        exc_trap = QtExceptionTrap()
        async_dsp = QtAsyncDispatcher(exc_trap)
        w_window = QMainWindow()
        tools = QtDialogTools(w_window)
        gui = QtGUI.from_window(w_window)
        ext = gui_cls(logger, async_dsp, tools, gui, **kwargs)
        exc_trap.connect(ext.handle_exception)
        wrap = exc_trap.wrap
        # Connect the GUI and all dialog menu items through the exception trap.
        gui.connect(wrap(ext.action))
        gui.menu_add(wrap(ext.open_translations), "File", "Load Translations...")
        gui.menu_add(wrap(ext.open_index), "File", "Load Index...")
        gui.menu_add(wrap(gui.close), "File", "Close", after_sep=True)
        gui.menu_add(wrap(ext.config_editor), "Tools", "Edit Configuration...")
        gui.menu_add(wrap(ext.custom_index), "Tools", "Make Index...")
        gui.menu_add(wrap(ext.debug_console), "Debug", "Open Console...")
        gui.menu_add(wrap(ext.debug_tree), "Debug", "View Object Tree...")
        gui.disable("Loading...")
        gui.show()
        # Build the app object asynchronously on a new thread to avoid blocking the GUI.
        async_dsp.dispatch(self.build_app, callback=ext.connect)
        return gui

    def main(self) -> int:
        """ Create a QApplication and load the GUI in standalone mode. """
        qt_app = QApplication(sys.argv)
        # The returned object must be assigned to a dummy local, or else Qt will garbage-collect it and crash...
        _ = self.build_gui(QtGUIExt)
        # After everything is loaded, start a GUI event loop and run it indefinitely.
        return qt_app.exec_()
