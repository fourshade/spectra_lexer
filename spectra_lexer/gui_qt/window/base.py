from typing import Callable, Iterable

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QCheckBox, QLabel, QLineEdit, QMainWindow
from pkg_resources import resource_filename

from .main_window_ui import Ui_MainWindow
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


class MainWindow(QMainWindow, Ui_MainWindow):
    """ Main GUI window. All GUI activity is coupled to this window. Controls all main view panels. """

    ICON_PATH = __package__, 'icon.svg'  # Package and relative file path for app icon.

    w_board: StenoBoardWidget
    w_desc: QLabel
    w_title: TextTitleWidget
    w_text: TextGraphWidget
    w_input: QLineEdit
    w_matches: SearchListWidget
    w_mappings: SearchListWidget
    w_strokes: QCheckBox
    w_regex: QCheckBox

    _state_vars: dict        # Contains a complete representation of the current state of the GUI.
    _update_gui: GUIUpdater  # Call with a dict to update the actual GUI widgets.
    _perform_action: Callable[[dict, str], dict]  # Main state processor callable.

    def __init__(self, perform_action:Callable) -> None:
        """ Create the window and map all GUI widgets to attributes.
            Connect all Qt signals and initialize the board size. """
        super().__init__()
        self.setupUi(self)
        # Set up the main window icon.
        fname = resource_filename(*self.ICON_PATH)
        icon = QIcon(fname)
        self.setWindowIcon(icon)
        self._perform_action = perform_action
        self._map_widgets()
        self._state_vars = {}
        self._update_gui = self._output_updater()
        for signal, action, *attrs in self._input_actions():
            def run(*values, _action=action, _attrs=attrs) -> None:
                """ Update the state (but not the GUI), then run the action. """
                self._state_vars.update(zip(_attrs, values))
                self.action(_action)
            signal.connect(run)
        self.show()
        self.set_enabled(True)

    def _map_widgets(self) -> None:
        """ Map all Python widget classes to internal Qt Designer names. """
        self.__dict__.update(w_board=self.w_display_board,
                             w_desc=self.w_display_desc,
                             w_title=self.w_display_title,
                             w_text=self.w_display_text,
                             w_input=self.w_search_input,
                             w_matches=self.w_search_matches,
                             w_mappings=self.w_search_mappings,
                             w_strokes=self.w_search_type,
                             w_regex=self.w_search_regex)

    def _input_actions(self) -> Iterable[tuple]:
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

    def _output_updater(self) -> GUIUpdater:
        """ Return a dict with all possible GUI methods to call when a particular part of the state changes. """
        return GUIUpdater(input_text=self.w_input.setText,
                          matches=self.w_matches.set_items,
                          match_selected=self.w_matches.select,
                          mappings=self.w_mappings.set_items,
                          mapping_selected=self.w_mappings.select,
                          translation=self.w_title.set_text,
                          graph_text=self.w_text.set_interactive_text,
                          board_caption=self.w_desc.setText,
                          board_xml_data=self.w_board.set_board_data,
                          link_ref=self.w_board.set_link)

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
        """ For a plugin window, this is called by its host application to re-open it. """
        super().show()
        self.activateWindow()
        self.raise_()

    def update(self, **kwargs) -> None:
        """ For every attribute given, update our state dict and the GUI widgets. """
        self._state_vars.update(kwargs)
        self._update_gui(kwargs)

    def action(self, action:str, **override) -> None:
        """ Send an action command with the current state. Parameters may be temporarily overridden by kwargs. """
        changed = self._perform_action({**self._state_vars, **override}, action)
        # After any action, run through the changes and update the state and widgets with any relevant ones.
        self.update(**changed)

    def status(self, status:str) -> None:
        """ Show GUI status messages in the title. """
        self.w_title.set_text(status)

    def exc_traceback(self, tb_text:str) -> None:
        """ Print an exception traceback to the main text widget. """
        self.w_title.set_text("Well, this is embarrassing...", dynamic=False)
        self.w_text.set_plaintext(tb_text)
