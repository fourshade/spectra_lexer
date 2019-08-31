""" Main entry point for Spectra's interactive GUI application. """

import sys
from threading import Thread
from traceback import format_exception
from typing import Any, Callable, Type

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

from .dialog import QtDialogFactory
from .window import QtWindow
from spectra_lexer import Spectra
from spectra_lexer.app import StenoApplication, StenoMain
from spectra_lexer.log import StreamLogger
from spectra_lexer.steno.analysis import IndexMapper


class QtDispatcher(QObject):
    """ Enables long-running operations on separate threads while keeping the GUI responsive. """

    sig_exception = pyqtSignal(Exception)  # Sent when an exception is encountered running protected code.

    _sig_done = pyqtSignal([object, object])  # Internal signal; used to send results back to the main thread.

    def __init__(self) -> None:
        super().__init__()
        self._sig_done.connect(self._on_async_done)

    def __enter__(self) -> None:
        """ Enter this object as a context manager to prevent exceptions from escaping the following code. """
        return None

    def __exit__(self, _, exc:BaseException, *args) -> bool:
        """ Catch any exception thrown by the wrapped code and send it off for logging/printing using the signal.
            Do NOT catch BaseExceptions - these are typically caused by the user wanting to exit the program. """
        if isinstance(exc, Exception):
            self.sig_exception.emit(exc)
            return True

    def protected(self, func:Callable) -> Callable:
        """ Qt may crash if Python exceptions propagate back to the event loop.
            This thread-safe wrapper takes care of exceptions before they make it back there. """
        def protected_call(*args) -> Any:
            with self:
                return func(*args)
        return protected_call

    def async_run(self, *args, **kwargs) -> None:
        """ Call a function on a new thread and disable the GUI while the thread is busy. """
        Thread(target=self._async_run, args=args, kwargs=kwargs, daemon=True).start()

    def _async_run(self, func:Callable, *args, callback:Callable=None, **kwargs) -> None:
        """ Run <func> with the given args/kwargs and send back results using a Qt signal.
            <callback>, if given, must accept the return value of this function as its only argument. """
        with self:
            value = func(*args, **kwargs)
            if callback is not None:
                self._sig_done.emit(callback, value)

    def _on_async_done(self, callback:Callable, value:Any) -> None:
        """ Call the callback on the main thread once the task is done. """
        with self:
            callback(value)


class QtTaskRunner:
    """ Runs async tasks, disabling the GUI while doing so. """

    def __init__(self, dsp:QtDispatcher, window:QtWindow) -> None:
        self._dsp = dsp
        self._window = window
        self._callback = None  # Callback to run on task complete.
        self._msg_out = None   # Message to show on task complete.

    def run(self, func, *args, callback=None, msg_in=None, msg_out:str=None, **kwargs) -> None:
        """ Show an optional status message, disable the GUI, and start the task. """
        self._window.set_enabled(False)
        if msg_in is not None:
            self._window.set_status(msg_in)
        self._callback = callback
        self._msg_out = msg_out
        self._dsp.async_run(func, *args, callback=self._on_finish, **kwargs)

    def _on_finish(self, value) -> None:
        """ Re-enable the GUI once the thread is clear and show a message. """
        self._window.set_enabled(True)
        if self._msg_out is not None:
            self._window.set_status(self._msg_out)
        if self._callback is not None:
            self._callback(value)


class QtExceptions:
    """ Display and tracks exceptions for the Qt GUI. Stores the last exception to be displayed by debug tools. """

    last_exception: Exception = None

    def __init__(self, logger:StreamLogger, window:QtWindow, *, max_frames:int=20) -> None:
        self._logger = logger
        self._window = window
        self._max_frames = max_frames  # Maximum number of stack frames to print/log.

    def handle(self, exc:Exception) -> None:
        """ Format, log, and display a stack trace. Save the exception for introspection. """
        self.last_exception = exc
        tb_text = "".join(format_exception(type(exc), exc, exc.__traceback__, limit=self._max_frames))
        self._logger.log('EXCEPTION\n' + tb_text)
        self._window.show_exception(tb_text)


class QtGUIState:
    """ Handles communication between the app's state machine and the Qt GUI's main widgets. """

    def __init__(self, app:StenoApplication, methods:dict) -> None:
        self._process = app.process_action  # Main state processor.
        self._methods = methods             # Dict of GUI methods to call with process output.
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
        for k in state_vars:
            if k in self._methods:
                self._methods[k](state_vars[k])

    def _action(self, state:dict, action:str) -> None:
        """ Send an action command with the given state. """
        changed = self._process(state, action)
        # After any action, run through the changes and update the state and widgets with any relevant ones.
        self._update(**changed)


class QtGUIDialogManager:
    """ Delegate for all tasks related to Qt dialog windows. """

    def __init__(self, app:StenoApplication, runner:QtTaskRunner, dialogs:QtDialogFactory) -> None:
        self._app = app
        self._run = runner.run
        self._dialogs = dialogs

    def open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self._dialogs.open_translations()
        if filenames:
            self._run(self._app.load_translations, *filenames, msg_out="Loaded translations from file dialog.")

    def open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self._dialogs.open_index()
        if filename:
            self._run(self._app.load_index, filename, msg_out="Loaded index from file dialog.")

    def config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        self._dialogs.config(self._update_config, self._app.get_config_info())

    def _update_config(self, options:dict) -> None:
        self._run(self._app.set_config, options, msg_out="Configuration saved.")

    def default_index(self) -> None:
        """ If there is no index file on first start, present a dialog for the user to make a default-sized index.
            Make the index on accept; otherwise save an empty one so the message doesn't appear again. """
        if self._dialogs.default_index():
            self._make_index(IndexMapper.DEFAULT_SIZE)
        else:
            self._make_index(0, msg_out="Skipped index creation.")

    def custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        self._dialogs.custom_index(self._make_index, IndexMapper.MINIMUM_SIZE, IndexMapper.MAXIMUM_SIZE,
                                   IndexMapper.DEFAULT_SIZE, IndexMapper.SIZE_DESCRIPTIONS)

    def _make_index(self, size:int, *, msg_out="Successfully created index!") -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self._run(self._app.make_index, size, msg_in="Making new index...", msg_out=msg_out)


class QtGUI:
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    def __init__(self, dsp:QtDispatcher, exceptions:QtExceptions,
                 window:QtWindow, runner:QtTaskRunner, **kwargs) -> None:
        self._protect = dsp.protected
        self.exceptions = exceptions
        self.window = window
        self.runner = runner
        self.app = None
        self.state = None
        self.dialogs = None

    def menu_add(self, menu_callback:Callable, *args, **kwargs) -> None:
        """ Qt may provide (useless) args to menu action callbacks. Throw them away. """
        self.window.menu_add(self._protect(lambda *_: menu_callback()), *args, **kwargs)

    def connect(self, app:StenoApplication) -> None:
        """ Once the user layer is loaded, it is safe to connect GUI extensions to it and enable it. """
        self.app = app
        window = self.window
        state = self.state = QtGUIState(app, window.methods())
        window.connect(self._protect(state.update_action))
        # Create the dialog container and connect all menu items.
        dlg_factory = QtDialogFactory(window.dialog_parent(), vars(self))
        dialogs = self.dialogs = QtGUIDialogManager(app, self.runner, dlg_factory)
        self.menu_add(dialogs.open_translations, "File", "Load Translations...", pos=0)
        self.menu_add(dialogs.open_index, "File", "Load Index...", pos=1)
        self.menu_add(dialogs.config_editor, "Tools", "Edit Configuration...")
        self.menu_add(dialogs.custom_index, "Tools", "Make Index...")
        self.menu_add(dlg_factory.console, "Debug", "Open Console...")
        self.menu_add(dlg_factory.objtree, "Debug", "View Object Tree...")
        # If there is no index file on first start, send up a dialog.
        if app.index_missing:
            dialogs.default_index()


class QtMain(StenoMain):
    """ Main entry point and factory for the Qt GUI. """

    def build_gui(self, gui_cls:Type[QtGUI], **kwargs) -> QtWindow:
        """ Load the user layer asynchronously on a new thread to avoid blocking the GUI. """
        logger = self.build_logger()
        dsp = QtDispatcher()
        window = QtWindow()
        runner = QtTaskRunner(dsp, window)
        exceptions = QtExceptions(logger, window)
        gui = gui_cls(dsp, exceptions, window, runner, **kwargs)
        dsp.sig_exception.connect(exceptions.handle)
        runner.run(self.build_app, callback=gui.connect, msg_in="Loading...", msg_out="Loading complete.")
        window.show()
        return window

    def main(self) -> int:
        """ Create a QApplication and load the GUI in standalone mode. """
        qt_app = QApplication(sys.argv)
        # The returned object must be assigned to a dummy local, or else Qt will garbage-collect it and crash...
        _ = self.build_gui(QtGUI)
        # After everything is loaded, start a GUI event loop and run it indefinitely.
        return qt_app.exec_()


# Standalone GUI Qt application entry point.
gui = Spectra(QtMain)
