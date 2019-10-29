from functools import partial
import pkgutil
from typing import Callable

from .main_window import MainWindow
from .main_window_ui import Ui_MainWindow


class QtWindow(Ui_MainWindow):
    """ Main GUI window controller with pre-defined Qt Designer widgets. """

    ICON_PATH = __package__, 'icon.svg'  # Package and relative file path for window icon.

    def __init__(self) -> None:
        """ Create the main window and call the UI setup method to add all widgets to this object as attributes. """
        self.window = window = MainWindow()  # Main Qt window.
        self.setupUi(window)
        icon_data = pkgutil.get_data(*self.ICON_PATH)
        window.load_icon(icon_data)
        self.show = window.show
        self.close = window.close
        self.set_status = self.w_title.set_status
        # Dict of all possible GUI methods to call when a particular part of the state changes.
        self._methods = {"input_text":       self.w_input.setText,
                         "matches":          self.w_matches.set_items,
                         "match_selected":   self.w_matches.select,
                         "mappings":         self.w_mappings.set_items,
                         "mapping_selected": self.w_mappings.select,
                         "translation":      self.w_title.set_translation,
                         "graph_text":       self.w_text.set_graph_text,
                         "board_caption":    self.w_desc.setText,
                         "board_xml_data":   self.w_board.set_data,
                         "link_ref":         self.w_board.set_link}
        # List of all GUI input events that can result in a call to a steno engine action.
        self._events = [(self.w_strokes.toggled, "Search", "mode_strokes"),
                        (self.w_regex.toggled, "Search", "mode_regex"),
                        (self.w_input.textEdited, "Search", "input_text"),
                        (self.w_matches.sig_select_item, "Lookup", "match_selected"),
                        (self.w_mappings.sig_select_item, "Select", "mapping_selected"),
                        (self.w_title.sig_edit_translation, "Query", "translation"),
                        (self.w_text.sig_over_ref, "GraphOver", "graph_node_ref"),
                        (self.w_text.sig_click_ref, "GraphClick", "graph_node_ref"),
                        (self.w_board.sig_activate_link, "SearchExamples", None),
                        (self.w_board.sig_new_ratio, "GraphOver", "board_aspect_ratio")]

    def menu_add(self, menu_callback:Callable, *args, **kwargs) -> None:
        """ Qt may provide (useless) args to menu action callbacks. Throw them away in a lambda. """
        self.w_menu.add(lambda *_: menu_callback(), *args, **kwargs)

    def connect(self, update_action:Callable) -> None:
        """ Connect all input signals to the function with their corresponding action and/or state attribute. """
        for signal, action, attr in self._events:
            fn = partial(update_action, action, attr)
            signal.connect(fn)
        # Initialize the board size after all connections are made.
        self.w_board.resizeEvent()

    def update(self, state_vars:dict) -> None:
        """ For every state variable given, call the corresponding GUI method if one exists. """
        for k in self._methods:
            if k in state_vars:
                self._methods[k](state_vars[k])

    def dialog_parent(self) -> MainWindow:
        """ Return a widget suitable for being the parent to dialogs. """
        return self.window

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all widgets when GUI-blocking operations are being done. """
        self.w_menu.setEnabled(enabled)
        self.w_input.setEnabled(enabled)
        self.w_matches.setEnabled(enabled)
        self.w_mappings.setEnabled(enabled)
        self.w_strokes.setEnabled(enabled)
        self.w_regex.setEnabled(enabled)
        self.w_title.setReadOnly(not enabled)
        self.w_text.setEnabled(enabled)
        self.w_board.set_link("")

    def show_exception(self, tb_text:str) -> None:
        """ Display a stack trace. Enable all widgets afterward to allow debugging. """
        self.w_title.setText("Well, this is embarrassing...")
        self.w_text.add_plaintext(tb_text)
        self.set_enabled(True)

    def start_blocking_task(self, callback:Callable=None, msg_done:str=None) -> Callable[..., None]:
        """ Disable the window controls in order to start a blocking task.
            Return a callback that will re-enable the controls and optionally show <msg_done> when the task is done.
            This may wrap another <callback> that will be called with the original arguments. """
        self.set_enabled(False)
        def on_task_finish(*args, **kwargs) -> None:
            self.set_enabled(True)
            if msg_done is not None:
                self.set_status(msg_done)
            if callback is not None:
                callback(*args, **kwargs)
        return on_task_finish
