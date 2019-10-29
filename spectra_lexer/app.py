from typing import Any, Dict, List

from .config import ConfigDictionary, ConfigItem, ConfigOption
from .io import ResourceIO
from .search import ExampleIndexInfo, SearchEngine
from .steno import StenoEngine


class SearchConfig:
    """ State attributes that can be user-configured (desktop), or sent in query strings (HTTP). """
    matches_per_page: int = ConfigOption("search", "match_limit", 100,
                                         "Maximum number of matches returned on one page of a search.")


class StenoConfig:
    """ State attributes that can be user-configured (desktop), or sent in query strings (HTTP). """
    board_compound: bool = ConfigOption("board", "compound_keys", True,
                                        "Show special labels for compound keys (i.e. `f` instead of TP).")
    graph_compress: bool = ConfigOption("graph", "compressed_layout", True,
                                        "Compress the graph layout vertically to save space.")
    graph_compat: bool = ConfigOption("graph", "compatibility_mode", False,
                                      "Force correct spacing in the graph using HTML tables.")
    match_all_keys: bool = ConfigOption("lexer", "need_all_keys", False,
                                        "Only return lexer results that match every key in the stroke.")


class ViewState(SearchConfig, StenoConfig):
    """ The primary GUI state machine. Contains a complete representation of the state of the main GUI operations.
        The general flow of information goes from the search box, to a list of words matching the search, to a list
        of mappings (strokes <-> translations) that correspond to the chosen word, and finally to the lexer.
        After the lexer is finished with a translation, a graph and board diagram are generated.
        Various steps of the process may be done automatically; for example, if there is only one
        possible mapping of a certain word, it will be chosen automatically and a lexer query sent. """

    _MORE_TEXT = "(more...)"  # Text displayed as the final list item, allowing the user to expand the search.
    _INDEX_DELIM = ";"        # Delimiter between rule name and query for example index searches.

    # Pure input values.
    mode_strokes: bool = False         # If True, search for strokes instead of translations.
    mode_regex: bool = False           # If True, perform search using regex characters.
    board_aspect_ratio: float = 100.0  # Last aspect ratio for board viewing area.

    # Either the program or user may manipulate the GUI to change these values.
    input_text: str = ""          # Last pattern from user textbox input.
    match_selected: str = ""      # Last selected match from the upper list.
    mapping_selected: str = ""    # Last selected match from the lower list.
    translation: list = ["", ""]  # Currently diagrammed translation on graph.
    graph_node_ref: str = ""      # Last node identifier on the graph ("" for empty space).

    # The user typically can't change these values directly. They are held for future reference.
    link_ref: str = ""             # Name for the most recent rule (if there are examples in the index).
    page_count: int = 1            # Number of pages in the upper list.
    graph_has_focus: bool = False  # Is a node under focus on the graph?

    # Pure output values.
    matches: list = []           # New items in the upper list.
    mappings: list = []          # New items in the lower list.
    graph_text: str = ""         # HTML formatted text for the graph.
    board_caption: str = ""      # Rule caption above the board.
    board_xml_data: bytes = b""  # Raw XML data string for an SVG board.

    def __init__(self, steno_engine:StenoEngine, search_engine:SearchEngine) -> None:
        self._steno_engine = steno_engine    # Has access to lexer and graphical components.
        self._search_engine = search_engine  # Has access to translations and example indices.
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
        link = self.link_ref
        selection = self._search_engine.find_example(link)[not self.mode_strokes]
        self.input_text = self._INDEX_DELIM.join([link, selection])
        self.page_count = 1
        self._search()
        if selection in self.matches:
            self.match_selected = selection
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
            count = self.page_count * self.matches_per_page
            matches = self._call_search(count=count, regex=self.mode_regex)
            # If we met the count, add a final item to allow search expansion.
            if len(matches) == count:
                matches.append(self._MORE_TEXT)
        # Set a new match list. This invalidates the previous mappings.
        self.matches = matches
        self.mappings = []

    def _lookup(self) -> None:
        """ Look up mappings and display them in the lower list. """
        match = self.match_selected
        # If count is None or unset, the search will find mappings instead of matches.
        mappings = self.mappings = self._call_search(match)
        if mappings:
            # A lone mapping should be highlighted automatically and displayed on its own.
            selection, *others = mappings
            if others:
                # If there is more than one mapping, make a query to select the best combination.
                selection = self._steno_engine.lexer_best_strokes(mappings, match)
            self.mapping_selected = selection
            self._query_from_selection()

    def _call_search(self, match=None, **kwargs) -> List[str]:
        kwargs["strokes"] = self.mode_strokes
        *prefix, pattern = self.input_text.split(self._INDEX_DELIM, 1)
        text = match or pattern
        if prefix:
            return self._search_engine.search_examples(*prefix, text, **kwargs)
        else:
            return self._search_engine.search_translations(text, **kwargs)

    def RUNSelect(self) -> None:
        """ Do a lexer query based on the current search selections. """
        self._query_from_selection()

    def _query_from_selection(self) -> None:
        """ The order of lexer parameters must be reversed for strokes mode. """
        self.translation = translation = [self.match_selected, self.mapping_selected]
        if not self.mode_strokes:
            translation.reverse()
        self._new_graph()

    def RUNQuery(self) -> None:
        """ Execute and display a graph of a lexer query from user strokes. """
        self._new_graph()

    def _new_graph(self) -> None:
        """ A new graph should clear the last node ref and look for a new one that uses the same rule. """
        self.graph_node_ref = ""
        self._exec_query(self.graph_has_focus, True)

    def RUNGraphOver(self) -> None:
        """ On mouseover, highlight the current graph node temporarily if nothing is focused.
            Mouseovers should do nothing as long as focus is active. """
        if not self.graph_has_focus:
            self._exec_query(False, False)

    def RUNGraphClick(self) -> None:
        """ On click, find the current graph node and set focus on it (or clear focus if None). """
        self._exec_query(False, True)

    def _exec_query(self, find_rule:bool, set_focus:bool) -> None:
        """ Execute a new lexer query and load the state with the output to draw the graph and board.
            If <set_focus> is True, lock onto any valid selection with a bright color.
            If <find_rule> is True, attempt to move focus to a node with the same rule as the previous one. """
        keys, letters = self.translation
        if not (keys and letters):
            return
        select_ref = self.link_ref if find_rule else self.graph_node_ref
        data = self._steno_engine.run(keys, letters,
                                      select_ref=select_ref,
                                      find_rule=find_rule,
                                      set_focus=set_focus,
                                      board_ratio=self.board_aspect_ratio,
                                      match_all_keys=self.match_all_keys,
                                      graph_compress=self.graph_compress,
                                      graph_compat=self.graph_compat,
                                      board_compound=self.board_compound)
        graph_text, has_focus, rule_name, caption, xml_data = data
        self.graph_text = graph_text
        self.graph_has_focus = has_focus
        self.link_ref = rule_name if self._search_engine.has_examples(rule_name) else ""
        self.board_caption = caption
        self.board_xml_data = xml_data


class StenoApplication:
    """ Common layer for user operations (resource I/O, GUI actions, batch analysis...it all goes through here). """

    def __init__(self, io:ResourceIO, steno_engine:StenoEngine, search_engine:SearchEngine) -> None:
        self._io = io                        # Handles all resource loading, saving, and transcoding.
        self._steno_engine = steno_engine    # Runtime engine for steno operations such as parsing and graphics.
        self._search_engine = search_engine  # Runtime engine for translation search operations.
        self._config = ConfigDictionary()    # Keeps track of configuration options in a master dict.
        cvars = {**vars(StenoConfig), **vars(SearchConfig)}
        for key, opt in cvars.items():
            if isinstance(opt, ConfigOption):
                self._config.add_option(key, opt)
        self._index_file = ""                # Holds filename for index; set on first load.
        self._config_file = ""               # Holds filename for config; set on first load.
        self.is_first_run = False            # Set to True if we fail to load the config file.

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge translations from disk. """
        translations = self._io.json_read_merge(*filenames)
        self.set_translations(translations)

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Send a new translations dict to the search engine and keep a copy for bulk analysis. """
        self._search_engine.set_translations(translations)

    def save_translations(self, translations:Dict[str, str], filename:str) -> None:
        """ Save a translations dict directly into JSON. """
        self._io.json_write(translations, filename)

    def load_index(self, filename:str) -> None:
        """ Load an examples index from disk. Ignore missing files. """
        self._index_file = filename
        try:
            index = self._io.json_read(filename)
            self.set_index(index)
        except OSError:
            pass

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Send a new examples index dict to the search engine. """
        self._search_engine.set_index(index)

    def save_index(self, index:Dict[str, dict]) -> None:
        """ Save an examples index structure directly into JSON. """
        assert self._index_file
        self._io.json_write(index, self._index_file)

    def make_rules(self, filename:str, **kwargs) -> None:
        """ Run the lexer on every item in the steno translations dictionary and save the rules to <filename>. """
        translations = self._search_engine.get_translations()
        raw_rules = self._steno_engine.make_rules(translations, **kwargs)
        self._io.json_write(raw_rules, filename)

    def make_index(self, size:int, **kwargs) -> None:
        """ Make a index for each built-in rule containing a dict of every translation that used it.
            Use an input filter to control size. Finish by setting them active and saving them to disk. """
        translations = self._search_engine.get_filtered_translations(size)
        index = self._steno_engine.make_index(translations, **kwargs)
        self.set_index(index)
        self.save_index(index)

    def get_index_info(self) -> ExampleIndexInfo:
        """ Return information about creating a new example index. """
        return self._search_engine.get_index_info()

    def load_config(self, filename:str) -> None:
        """ Load config settings from disk. If the file is missing, set a 'first run' flag and start a new one. """
        self._config_file = filename
        try:
            cfg = self._io.cfg_read(filename)
            self._config.update_from_cfg(cfg)
        except OSError:
            self.is_first_run = True
            self.set_config()

    def set_config(self, options:Dict[str, Any]=None) -> None:
        """ Update the config dict with <options> (if any), and save them to disk. """
        assert self._config_file
        if options:
            self._config.update(options)
        cfg = self._config.to_cfg_sections()
        self._io.cfg_write(cfg, self._config_file)

    def get_config_info(self) -> List[ConfigItem]:
        """ Return all active config info with formatting instructions. """
        return self._config.info()

    def process_action(self, state:Dict[str, Any], action:str) -> dict:
        """ Perform an <action> on an initial view <state>, then return the changes.
            Config options are added to the view state first. The main state variables may override them. """
        view_state = ViewState(self._steno_engine, self._search_engine)
        view_state.update(self._config)
        view_state.update(state)
        view_state.run(action)
        return view_state.get_modified()
