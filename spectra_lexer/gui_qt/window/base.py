import pkgutil
from typing import Callable, Dict, List

from PyQt5.QtWidgets import QCheckBox, QLabel, QLineEdit

from .main_window import MainWindow
from .search_list_widget import SearchListWidget
from .steno_board_widget import StenoBoardWidget
from .text_graph_widget import TextGraphWidget
from .text_title_widget import TextTitleWidget


class GUIUpdater(dict):
    """ Mapping with GUI methods to call when a particular part of the state changes. """

    def __call__(self, attrs:dict) -> None:
        """ For every attribute given, call the corresponding GUI method if one exists. """
        for k in attrs:
            if k in self:
                self[k](attrs[k])


class QtGUI:
    """ Main GUI window controller. All GUI activity is coupled to this object. Controls all main view panels. """

    ICON_PATH = __package__, 'icon.svg'  # Package and relative file path for app icon.

    window: MainWindow
    w_board: StenoBoardWidget
    w_desc: QLabel
    w_title: TextTitleWidget
    w_text: TextGraphWidget
    w_input: QLineEdit
    w_matches: SearchListWidget
    w_mappings: SearchListWidget
    w_strokes: QCheckBox
    w_regex: QCheckBox

    _perform_action: Callable[[dict, str], dict]  # Main state processor callable.
    _state_vars: dict        # Contains a complete representation of the current state of the GUI.
    _update_gui: GUIUpdater  # Call with a dict to update the actual GUI widgets.

    def __init__(self, perform_action:Callable) -> None:
        """ Create the window and map all GUI widgets to attributes.
            Connect all Qt signals and initialize the board size. """
        window = self.window = MainWindow()
        widgets = window.map_widgets()
        self.__dict__.update(widgets)
        data = pkgutil.get_data(*self.ICON_PATH)
        self.window.load_icon(data)
        self._perform_action = perform_action
        self._state_vars = {}
        self._update_gui = GUIUpdater(self._output_methods())
        for signal_params in self._input_actions():
            self._connect(*signal_params)
        self.set_enabled(True)

    def _output_methods(self) -> Dict[str, Callable]:
        """ Return a dict with all possible GUI methods to call when a particular part of the state changes. """
        return dict(input_text=self.w_input.setText,
                    matches=self.w_matches.set_items,
                    match_selected=self.w_matches.select,
                    mappings=self.w_mappings.set_items,
                    mapping_selected=self.w_mappings.select,
                    translation=self.w_title.set_text,
                    graph_text=self.w_text.set_interactive_text,
                    board_caption=self.w_desc.setText,
                    board_xml_data=self.w_board.set_board_data,
                    link_ref=self.w_board.set_link)

    def _input_actions(self) -> List[tuple]:
        """ Return all possible user input signals and the corresponding actions with any state updates. """
        return [(self.w_strokes.toggled,       "Search",     "mode_strokes"),
                (self.w_regex.toggled,         "Search",     "mode_regex"),
                (self.w_input.textEdited,      "Search",     "input_text"),
                (self.w_matches.itemSelected,  "Lookup",     "match_selected"),
                (self.w_mappings.itemSelected, "Select",     "mapping_selected"),
                (self.w_title.textEdited,      "Query",      "translation"),
                (self.w_text.graphOver,        "GraphOver",  "graph_node_ref"),
                (self.w_text.graphClick,       "GraphClick", "graph_node_ref"),
                (self.w_board.onActivateLink,  "SearchExamples"),
                (self.w_board.onResize,        "GraphOver",  "board_aspect_ratio")]

    def _connect(self, signal, action:str, *attrs:str) -> None:
        """ Connect a Qt signal to an action callback. """
        def run(*values) -> None:
            """ Update the state (but not the GUI), then run the action. """
            self._state_vars.update(zip(attrs, values))
            self.action(action)
        signal.connect(run)

    def reset(self) -> None:
        """ Reset all interactive GUI widgets with the default (blank) value. """
        self.update(input_text="", matches=[], mappings=[], translation="", graph_text="", link_ref="")

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all widgets when GUI-blocking operations are being done. """
        if not enabled:
            self.reset()
        self.w_input.setEnabled(enabled)
        self.w_input.setPlaceholderText("Search..." if enabled else "")
        self.w_matches.setEnabled(enabled)
        self.w_mappings.setEnabled(enabled)
        self.w_strokes.setEnabled(enabled)
        self.w_regex.setEnabled(enabled)
        self.w_title.setReadOnly(not enabled)
        self.w_board.resizeEvent()

    def show(self) -> None:
        self.window.show()

    def close(self) -> None:
        self.window.close()

    def update(self, **kwargs) -> None:
        """ For every attribute given, update our state dict and the GUI widgets. """
        self._state_vars.update(kwargs)
        self._update_gui(kwargs)

    def action(self, action:str, **override) -> None:
        """ Send an action command with the current state. Parameters may be temporarily overridden by kwargs. """
        self._perform_action({**self._state_vars, **override}, action, qt_callback=self.on_action_done)

    def on_action_done(self, changed:dict) -> None:
        # After any action, run through the changes and update the state and widgets with any relevant ones.
        self.update(**changed)

    def status(self, status:str) -> None:
        """ Show GUI status messages in the title. """
        self.w_title.set_text(status)

    def exc_traceback(self, tb_text:str) -> None:
        """ Print an exception traceback to the main text widget. """
        self.w_title.set_text("Well, this is embarrassing...", dynamic=False)
        self.w_text.set_plaintext(tb_text)
