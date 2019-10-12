""" Main entry point for Spectra's interactive GUI application. """

import sys
from threading import Thread
from traceback import format_exception
from typing import Any, Callable, Type

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

from .dialog import QtDialogFactory
from .window import QtWindow
from spectra_lexer.app import StenoApplication, StenoMain
from spectra_lexer.log import StreamLogger


class QtExceptionTrap(QObject):
    """ Traps exceptions for the Qt GUI and emits them as signals. """

    _sig_traceback = pyqtSignal([Exception])  # Sent when an exception is encountered in protected code.

    def __init__(self) -> None:
        super().__init__()
        self.connect = self._sig_traceback.connect

    def __enter__(self) -> None:
        """ Qt may crash if Python exceptions propagate back to the event loop.
            Enter this object as a context manager to prevent exceptions from escaping the following code. """
        return None

    def __exit__(self, _, exc:BaseException, *args) -> bool:
        """ Emit any thrown exception as a Qt signal.
            Do NOT catch BaseExceptions - these are typically caused by the user wanting to exit the program. """
        if isinstance(exc, Exception):
            self._sig_traceback.emit(exc)
            return True

    def wrap(self, func:Callable) -> Callable[..., None]:
        """ Wrap a callable to trap and emit any exceptions propagating from it. It will not return a value. """
        def trapped_call(*args, **kwargs) -> None:
            with self:
                func(*args, **kwargs)
        return trapped_call


class QtAsyncDispatcher(QObject):
    """ Enables long-running operations on separate threads while keeping the GUI responsive. """

    _sig_done = pyqtSignal([object, object])  # Internal signal; used to send results back to the main thread.

    def __init__(self, exc_trap:QtExceptionTrap) -> None:
        super().__init__()
        self._exc_trap = exc_trap
        self._sig_done.connect(self._done)

    def dispatch(self, *args, **kwargs) -> None:
        """ Call a function on a new thread. """
        Thread(target=self._run, args=args, kwargs=kwargs, daemon=True).start()

    def _run(self, func:Callable, *args, callback:Callable=None, **kwargs) -> None:
        """ Run <func> with the given args/kwargs and send back results using a Qt signal.
            <callback>, if given, must accept the return value of this function as its only argument. """
        with self._exc_trap:
            value = func(*args, **kwargs)
            if callback is not None:
                self._sig_done.emit(callback, value)

    def _done(self, callback:Callable, value:Any) -> None:
        """ Call the callback on the main thread once the task is done. """
        with self._exc_trap:
            callback(value)


class QtGUIState:
    """ Handles communication between the app's state machine and the Qt GUI's main widgets. """

    def __init__(self, app:StenoApplication, window:QtWindow) -> None:
        self._process = app.process_action  # Main state processor.
        self._methods = window.methods()    # Dict of GUI methods to call with process output.
        self._state_vars = {}               # Contains a complete representation of the current state of the GUI.

    def query(self, strokes:str, word:str) -> None:
        """ Run a lexer query on actual user strokes from a steno machine. """
        self._update(translation=[strokes, word])
        state = {"match_all_keys": False, **self._state_vars}
        self._action(state, "Query")

    def update_action(self, action:str, attr:str=None, value:Any=None) -> None:
        """ Update the state with a value from a GUI event, then run the action. """
        state = self._state_vars
        if attr is not None:
            state[attr] = value
        self._action(state, action)

    def _update(self, **state_vars) -> None:
        """ For every variable given, update our state dict and call the corresponding GUI method if one exists. """
        self._state_vars.update(state_vars)
        for k in self._methods:
            if k in state_vars:
                self._methods[k](state_vars[k])

    def _action(self, state:dict, action:str) -> None:
        """ Send an action command with the given state. """
        changed = self._process(state, action)
        # After any action, run through the changes and update the state and widgets with any relevant ones.
        self._update(**changed)


class QtGUI:
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: Exception = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, logger:StreamLogger, exc_trap:QtExceptionTrap, async_dsp:QtAsyncDispatcher,
                 window:QtWindow, dialogs:QtDialogFactory, **kwargs) -> None:
        self.logger = logger
        self.exc_trap = exc_trap
        self.async_dsp = async_dsp
        self.window = window
        self.dialogs = dialogs
        self.app = None
        self.state = None

    def start(self, app_builder:Callable[[], StenoApplication]) -> None:
        """ Connect all dialog menu items through the exception trap. """
        exc_trap = self.exc_trap
        exc_trap.connect(self._handle_exception)
        def menu_add(menu_callback:Callable, *args, **kwargs) -> None:
            self.window.menu_add(exc_trap.wrap(menu_callback), *args, **kwargs)
        menu_add(self._open_translations, "File", "Load Translations...")
        menu_add(self._open_index, "File", "Load Index...")
        menu_add(self.window.close, "File", "Close", after_sep=True)
        menu_add(self._config_editor, "Tools", "Edit Configuration...")
        menu_add(self._custom_index, "Tools", "Make Index...")
        menu_add(self._debug_console, "Debug", "Open Console...")
        menu_add(self._debug_tree, "Debug", "View Object Tree...")
        # Build the app object asynchronously on a new thread to avoid blocking the GUI.
        self.window.set_status("Loading...")
        self._run_async(app_builder, callback=self._connect, msg_done="Loading complete.")
        self.window.show()

    def _connect(self, app:StenoApplication) -> None:
        """ Once the app object is loaded, it is safe to connect GUI extensions. """
        self.app = app
        window = self.window
        state = self.state = QtGUIState(app, window)
        window.connect(self.exc_trap.wrap(state.update_action))
        self._subcls_tasks()
        # If there is no index file on first start, send up a dialog.
        if app.is_first_run:
            self._default_index()

    def _subcls_tasks(self) -> None:
        """ Perform subclass-specific setup. """
        pass

    def _open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self.dialogs.open_translations_files()
        if filenames:
            self._run_async(self.app.load_translations, *filenames, msg_done="Loaded translations from file dialog.")

    def _open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self.dialogs.open_index_file()
        if filename:
            self._run_async(self.app.load_index, filename, msg_done="Loaded index from file dialog.")

    def _config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        self.dialogs.config(self._update_config, self.app.get_config_info())

    def _update_config(self, options:dict) -> None:
        self._run_async(self.app.set_config, options, msg_done="Configuration saved.")

    def _default_index(self) -> None:
        """ On first start, present a dialog for the user to make a default-sized index on accept. """
        if self.dialogs.confirm_startup_index():
            self._make_index()

    def _custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        self.dialogs.custom_index(self._make_index, self.app.get_index_info())

    def _make_index(self, size:int=None) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self.window.set_status("Making new index...")
        self._run_async(self.app.make_index, size, msg_done="Successfully created index!")

    def _debug_console(self) -> None:
        """ Create and show the debug console dialog. """
        self.dialogs.console(vars(self).copy())

    def _debug_tree(self) -> None:
        """ Create and show the debug tree dialog. """
        self.dialogs.objtree(vars(self).copy())

    def _run_async(self, func:Callable, *args, **kwargs) -> None:
        """ Start a blocking async task. """
        on_finish = self.window.start_blocking_task(**kwargs)
        self.async_dsp.dispatch(func, *args, callback=on_finish)

    def _handle_exception(self, exc:Exception, max_frames=20) -> None:
        """ Format, log, and display a stack trace for any thrown exception. Store the exception for introspection. """
        self.last_exception = exc
        tb_text = "".join(format_exception(type(exc), exc, exc.__traceback__, limit=max_frames))
        self.logger.log('EXCEPTION\n' + tb_text)
        self.window.show_exception(tb_text)


class QtMain(StenoMain):
    """ Main entry point and factory for the Qt GUI. """

    def build_gui(self, gui_cls:Type[QtGUI], **kwargs) -> QtWindow:
        """ Build all components necessary to operate the GUI. """
        logger = self.build_logger()
        exc_trap = QtExceptionTrap()
        dsp = QtAsyncDispatcher(exc_trap)
        window = QtWindow()
        dialogs = QtDialogFactory(window.dialog_parent())
        gui_cls(logger, exc_trap, dsp, window, dialogs, **kwargs).start(self.build_app)
        return window

    def main(self) -> int:
        """ Create a QApplication and load the GUI in standalone mode. """
        qt_app = QApplication(sys.argv)
        # The returned object must be assigned to a dummy local, or else Qt will garbage-collect it and crash...
        _ = self.build_gui(QtGUI)
        # After everything is loaded, start a GUI event loop and run it indefinitely.
        return qt_app.exec_()


# Standalone GUI Qt application entry point.
gui = QtMain()
