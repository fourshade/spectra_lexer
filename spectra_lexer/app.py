import json
from typing import Any, Dict, List

from .config import ConfigDictionary, ConfigItem
from .io import ResourceIO
from .steno import SearchResults, StenoAnalysisPage, StenoEngine


class StenoApplication:
    """ Common layer for user operations (resource I/O, GUI actions, batch analysis...it all goes through here). """

    def __init__(self, io:ResourceIO, engine:StenoEngine, config:ConfigDictionary) -> None:
        self._io = io              # Handles all resource loading, saving, and transcoding.
        self._engine = engine      # Runtime engine for steno operations such as parsing and graphics.
        self._config = config      # Keeps track of configuration options in a master dict.
        self._index_file = ""      # Holds filename for index; set on first load.
        self._config_file = ""     # Holds filename for config; set on first load.
        self.is_first_run = False  # Set to True if we fail to load the config file.

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge translations from JSON files. """
        translations = {}
        for filename in filenames:
            with self._io.open(filename, 'r') as fp:
                d = json.load(fp)
            translations.update(d)
        self.set_translations(translations)

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Send a new translations dict to the engine. """
        self._engine.set_translations(translations)

    def load_index(self, filename:str) -> None:
        """ Load an examples index from a JSON file. Ignore missing files. """
        self._index_file = filename
        try:
            with self._io.open(filename, 'r') as fp:
                index = json.load(fp)
            self.set_index(index)
        except OSError:
            pass

    def make_index(self, *args, **kwargs) -> None:
        """ Make a index for each built-in rule containing a dict of every translation that used it.
            Finish by setting them active and saving them to disk. """
        index = self._engine.make_index(*args, **kwargs)
        self.set_index(index)
        self.save_index(index)

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Send a new examples index dict to the engine. """
        self._engine.set_index(index)

    def save_index(self, index:Dict[str, dict]) -> None:
        """ Save an examples index structure to a JSON file.
            Dict key sorting helps search algorithms run faster.
            An explicit flag is required to preserve Unicode symbols. """
        assert self._index_file
        data = json.dumps(index, sort_keys=True, ensure_ascii=False)
        with self._io.open(self._index_file, 'w') as fp:
            fp.write(data)

    def load_config(self, filename:str) -> None:
        """ Load config settings from a CFG file.
            If the file is missing, set a 'first run' flag and start a new one. """
        self._config_file = filename
        try:
            with self._io.open(filename, 'r') as fp:
                self._config.read_cfg(fp)
        except OSError:
            self.is_first_run = True
            self.save_config()

    def set_config(self, options:Dict[str, Any]) -> None:
        """ Update the config dict with <options> and save them to disk. """
        self._config.update(options)
        self.save_config()

    def save_config(self) -> None:
        """ Save config settings into a CFG file. """
        assert self._config_file
        with self._io.open(self._config_file, 'w') as fp:
            self._config.write_cfg(fp)

    def get_config_info(self) -> List[ConfigItem]:
        """ Return all active config info with formatting instructions. """
        return self._config.info()

    def process_action(self, state:Dict[str, Any], action:str) -> dict:
        """ Perform an <action> on an initial view <state>, then return the changes.
            Config options are added to the view state first. The main state variables may override them. """
        view_state = ViewState(self._engine)
        view_state.update(self._config.to_dict())
        view_state.update(state)
        view_state.run(action)
        return view_state.get_modified()


class ViewState:
    """ The primary GUI state machine. Contains a complete representation of the state of the main GUI operations.
        The general flow of information goes from the search box, to a list of words matching the search, to a list
        of mappings (strokes <-> translations) that correspond to the chosen word, and finally to the lexer.
        After the lexer is finished with a translation, a graph and board diagram are generated.
        Various steps of the process may be done automatically; for example, if there is only one
        possible mapping of a certain word, it will be chosen automatically and a lexer query sent. """

    _MORE_TEXT = "(more...)"  # Text displayed as the final list item, allowing the user to expand the search.
    _INDEX_DELIM = ";"        # Delimiter between rule name and query for example index searches.

    # Pure input values (search).
    search_mode_strokes: bool = False  # If True, search for strokes instead of translations.
    search_mode_regex: bool = False    # If True, perform search using regex characters.
    search_match_limit: int = 100      # Maximum number of matches returned on one page of a search.

    # Pure input values (display).
    lexer_strict_mode: bool = False         # Only return lexer results that match every key in a translation.
    board_aspect_ratio: float = 100.0       # Aspect ratio for board viewing area.
    board_compound_key_labels: bool = True  # Show special labels for compound keys (i.e. `f` instead of TP).
    graph_compressed_layout: bool = True    # Compress the graph layout vertically to save space.
    graph_compatibility_mode: bool = False  # Force correct spacing in the graph using HTML tables.

    # Either the program or user may manipulate the GUI to change these values.
    input_text: str = ""          # Last pattern from user textbox input.
    match_selected: str = ""      # Last selected match from the upper list.
    mapping_selected: str = ""    # Last selected match from the lower list.
    translation: list = ["", ""]  # Currently diagrammed translation on graph.
    graph_node_ref: str = ""      # Last node identifier on the graph ("" for empty space).

    # The user typically can't change these values directly. They are held for future reference.
    page_count: int = 1            # Number of pages in the upper list.
    graph_has_focus: bool = False  # Is a node under focus on the graph?
    link_ref: str = ""             # Name for the most recent rule (if there are examples in the index).

    # Pure output values. These may be data classes that cannot be converted back from JSON.
    matches: list            # New items in the upper list.
    mappings: list           # New items in the lower list.
    page: StenoAnalysisPage  # Contains an HTML formatted graph, a caption, and an SVG board.

    def __init__(self, steno_engine:StenoEngine) -> None:
        self._steno_engine = steno_engine    # Has access to lexer and graphical components.
        self._modified = {}                  # Tracks attributes that are changed by action methods.

    def __setattr__(self, name:str, value:Any) -> None:
        """ Add public attributes that are modified to the tracking dict. """
        super().__setattr__(name, value)
        if not name.startswith("_"):
            self._modified[name] = value

    def update(self, *args, **kwargs) -> None:
        """ Update state attributes without affecting the modified tracker. """
        self.__dict__.update(*args, **kwargs)

    def get_modified(self) -> dict:
        """ Return all state attributes that have been modified, then reset the tracker. """
        last_modified = self._modified
        self._modified = {}
        return last_modified

    def run(self, action:str) -> None:
        """ Run an action method (if valid). """
        method = getattr(self, f"RUN{action}")
        method()

    def RUNSearchExamples(self) -> None:
        """ When a link is clicked, search for examples of the named rule and select one. """
        self.input_text = self.link_ref + self._INDEX_DELIM
        self.page_count = 1
        self._search()
        matches = self.matches
        if matches:
            match = self.match_selected = matches[len(matches)//2]
            self.input_text += match
            self._search()
            self._lookup()

    def RUNSearch(self) -> None:
        """ Do a new search unless the input is blank. """
        self.page_count = 1
        self._search()
        # Automatically select the match if there was only one.
        if len(self.matches) == 1:
            self.match_selected = self.matches[0]
            self._lookup()

    def RUNLookup(self) -> None:
        """ If the user clicked "more", search again with another page. """
        if self.match_selected == self._MORE_TEXT:
            self.page_count += 1
            self._search()
        else:
            self._lookup()

    def _search(self) -> None:
        """ Look up a pattern in the dictionary and populate the upper matches list unless the input is blank. """
        if not self.input_text:
            matches = []
        else:
            results = self._call_search()
            matches = results.matches
            # If we met the count, add a final item to allow search expansion.
            if not results.is_complete:
                matches.append(self._MORE_TEXT)
        # Set a new match list. This invalidates the previous mappings.
        self.matches = matches
        self.mappings = []

    def _lookup(self) -> None:
        """ Look up mappings and display them in the lower list. """
        match = self.match_selected
        results = self._call_search()
        matches = results.matches
        if match in matches:
            idx = results.matches.index(match)
            mappings = self.mappings = results.mappings[idx]
            if mappings:
                # A lone mapping should be highlighted automatically and displayed on its own.
                selection, *others = mappings
                if others:
                    # If there is more than one mapping, make a query to select the best combination.
                    selection = self._steno_engine.lexer_best_strokes(mappings, match)
                self.mapping_selected = selection
                self._query_from_selection()

    def _call_search(self) -> SearchResults:
        pattern = self.input_text
        kwargs = dict(count=self.page_count * self.search_match_limit, strokes=self.search_mode_strokes)
        if self._INDEX_DELIM in pattern:
            args = pattern.split(self._INDEX_DELIM, 1)
            return self._steno_engine.search_examples(*args, **kwargs)
        else:
            return self._steno_engine.search_translations(pattern, regex=self.search_mode_regex, **kwargs)

    def RUNSelect(self) -> None:
        """ Do a lexer query based on the current search selections. """
        self._query_from_selection()

    def _query_from_selection(self) -> None:
        """ The order of lexer parameters must be reversed for strokes mode. """
        self.translation = translation = [self.match_selected, self.mapping_selected]
        if not self.search_mode_strokes:
            translation.reverse()
        self._new_graph()

    def RUNQuery(self) -> None:
        """ Execute and display a graph of a lexer query from user strokes. """
        self._new_graph()

    def _new_graph(self) -> None:
        """ A new graph should clear the last node ref and look for a new one that uses the same rule. """
        self.graph_node_ref = ""
        self._exec_query(self.graph_has_focus, True)
        if not self.link_ref:
            self.graph_has_focus = False

    def RUNGraphOver(self) -> None:
        """ On mouseover, highlight the current graph node temporarily if nothing is focused.
            Mouseovers should do nothing as long as focus is active. """
        if not self.graph_has_focus:
            self._exec_query(False, False)

    def RUNGraphClick(self) -> None:
        """ On click, find the current graph node and set focus on it (or clear focus if node ref is empty). """
        self._exec_query(False, True)
        self.graph_has_focus = bool(self.graph_node_ref)

    def _exec_query(self, find_rule:bool, intense:bool) -> None:
        """ Execute a new lexer query and load the state with the output to draw the graph and board.
            If <find_rule> is True, attempt to select a node with the same rule as the previous one.
            If <intense> is True, draw any valid selection with a bright color. """
        keys, letters = self.translation
        if not (keys and letters):
            return
        select_ref = self.link_ref if find_rule else self.graph_node_ref
        page = self._steno_engine.analyze(keys, letters,
                                          match_all_keys=self.lexer_strict_mode,
                                          select_ref=select_ref,
                                          find_rule=find_rule,
                                          graph_compress=self.graph_compressed_layout,
                                          graph_compat=self.graph_compatibility_mode,
                                          graph_intense=intense,
                                          board_ratio=self.board_aspect_ratio,
                                          board_compound=self.board_compound_key_labels)
        self.page = page
        self.link_ref = page.rule_id
