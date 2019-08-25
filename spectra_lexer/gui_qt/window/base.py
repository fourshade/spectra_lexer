from functools import partial
import pkgutil
from typing import Any, Callable, Dict

from .main_window import MainWindow
from .main_window_ui import Ui_MainWindow

PROC_TP = Callable[[dict, str], dict]  # Action processor function type.
DECO_TP = Callable[[Callable], Callable]    # Decorator function type.


class WindowController(Ui_MainWindow):
    """ Main GUI window controller with pre-defined Qt designer widgets. """

    ICON_PATH = __package__, 'icon.svg'  # Package and relative file path for window icon.

    _window: MainWindow
    _state_vars: Dict[str, Any]      # Contains a complete representation of the current state of the GUI.
    _methods: Dict[str, Callable]    # Dict of GUI methods to call with process output.
    _perform_action: PROC_TP = None  # Main state processor callable.

    def __init__(self) -> None:
        """ Create the main window and call the UI setup method to add all widgets to this object as attributes. """
        window = self._window = MainWindow()
        self.setupUi(window)
        icon_data = pkgutil.get_data(*self.ICON_PATH)
        window.load_icon(icon_data)
        self.show = self._window.show
        self.close = self._window.close
        self.menu_add = self.w_menu.add
        self.set_status = self.w_title.set_status
        # Make a dict with all possible GUI methods to call when a particular part of the state changes.
        self._state_vars = {}
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

    def connect(self, perform_action:PROC_TP, exc_protector:DECO_TP) -> None:
        """ Make a list of all GUI input events that can result in a call to a steno engine action.
            Connect all input signals to the function with their corresponding action and/or state attribute.
            Run each generated function through <exc_protector> to stop exceptions from crashing Qt. """
        self._perform_action = perform_action
        events = [(self.w_strokes.toggled, "Search", "mode_strokes"),
                  (self.w_regex.toggled, "Search", "mode_regex"),
                  (self.w_input.textEdited, "Search", "input_text"),
                  (self.w_matches.sig_select_item, "Lookup", "match_selected"),
                  (self.w_mappings.sig_select_item, "Select", "mapping_selected"),
                  (self.w_title.sig_edit_translation, "Query", "translation"),
                  (self.w_text.sig_over_ref, "GraphOver", "graph_node_ref"),
                  (self.w_text.sig_click_ref, "GraphClick", "graph_node_ref"),
                  (self.w_board.sig_activate_link, "SearchExamples", None),
                  (self.w_board.sig_new_ratio, "GraphOver", "board_aspect_ratio")]
        for signal, action, attr in events:
            fn = partial(self._update_action, action, attr)
            signal.connect(exc_protector(fn))
        # Initialize the board size after all connections are made.
        self.w_board.resizeEvent()

    def _update_action(self, action:str, attr:str=None, value:Any=None) -> None:
        """ Update the state with a value from a GUI event, then run the action. """
        state = self._state_vars
        if attr is not None:
            state[attr] = value
        self._action(state, action)

    def dialog_parent(self) -> MainWindow:
        """ Return a widget suitable for being the parent to dialogs. """
        return self._window

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all widgets when GUI-blocking operations are being done.
            Reset all interactive GUI widgets with the default (blank) value on disable. """
        if not enabled:
            self._update(input_text="", matches=[], mappings=[], translation=["", ""], graph_text="", link_ref="")
        self.w_menu.setEnabled(enabled)
        self.w_input.setEnabled(enabled)
        self.w_matches.setEnabled(enabled)
        self.w_mappings.setEnabled(enabled)
        self.w_strokes.setEnabled(enabled)
        self.w_regex.setEnabled(enabled)
        self.w_title.setReadOnly(not enabled)
        self.w_text.setEnabled(enabled)

    def show_traceback(self, tb_text:str) -> None:
        """ Print an exception traceback to the main text widget. Enable all widgets afterward to allow debugging. """
        self.w_title.setText("Well, this is embarrassing...")
        self.w_text.add_plaintext(tb_text)
        self.set_enabled(True)

    def user_query(self, strokes:str, text:str) -> None:
        """ Send a lexer query derived from actual user strokes on a steno machine.
            User strokes may involve all sorts of custom briefs, so do not attempt to match every key. """
        self._update(translation=[strokes, text])
        state = {"match_all_keys": False, **self._state_vars}
        self._action(state, "Query")

    def _update(self, **state_vars) -> None:
        """ For every variable given, update our state dict and call the corresponding GUI method if one exists. """
        self._state_vars.update(state_vars)
        for k in state_vars:
            if k in self._methods:
                self._methods[k](state_vars[k])

    def _action(self, state:dict, action:str) -> None:
        """ If the callback is connected, send an action command with the given state. """
        if self._perform_action is not None:
            changed = self._perform_action(state, action)
            # After any action, run through the changes and update the state and widgets with any relevant ones.
            self._update(**changed)
