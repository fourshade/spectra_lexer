from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from .board import BoardEngine
from .filter import TranslationSizeFilter
from .graph import GraphEngine
from .keys import KeyLayout
from .lexer import LexerResult, StenoLexer
from .parallel import ParallelMapper
from .search import SearchEngine

_RAW_RULES_TP = Dict[str, list]
_TR_DICT_TP = Dict[str, str]


class StenoEngine:
    """ Main access point for steno analysis. Generates rules from translations and creates visual representations. """

    def __init__(self, layout:KeyLayout, search_engine:SearchEngine, lexer:StenoLexer,
                 board_engine:BoardEngine, graph_engine:GraphEngine, captions:Dict[str, str]) -> None:
        self._layout = layout                # Converts between user RTFCRE steno strings and s-keys.
        self._search_engine = search_engine  # Runtime engine for translation search operations.
        self._lexer = lexer
        self._board_engine = board_engine
        self._graph_engine = graph_engine
        self._captions = captions

    def set_translations(self, translations:Dict[str, str]) -> None:
        """ Send a new translations dict to the search engine. """
        self._search_engine.set_translations(translations)

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Send a new examples index dict to the search engine. """
        self._search_engine.set_index(index)

    def process_action(self, state:Dict[str, Any], action:str) -> dict:
        """ Perform an <action> on an initial view <state>, then return the changes. """
        view_state = ViewState(self, self._search_engine)
        view_state.update(state)
        view_state.run(action)
        return view_state.get_modified()

    def run(self, keys:str, letters:str, *,
            select_ref:str, find_rule:bool, set_focus:bool, board_ratio:float, match_all_keys:bool,
            graph_compress:bool, graph_compat:bool, board_compound:bool):
        """ Run a lexer query and return everything necessary to update the user GUI state. """
        result = self.lexer_query(keys, letters, match_all_keys=match_all_keys)
        unmatched_skeys = result.unmatched_skeys()
        connections = list(result)
        # Convert unmatched keys back to RTFCRE format for the graph and caption.
        unmatched_keys = self._layout.to_rtfcre(unmatched_skeys)
        root = self._graph_engine.make_tree(letters, connections, unmatched_keys)
        target = None
        for node in root:
            ref = node.rule() if find_rule else node.ref()
            if ref == select_ref:
                target = node
                break
        text = root.render(target, compressed=graph_compress, compat=graph_compat, intense=set_focus)
        # If nothing is selected, remove any focus and generate a board and caption for the root node by default.
        if target is None:
            target = root
            set_focus = False
        rule_name = target.rule()
        if target is root:
            caption = result.caption()
            names = result.rules()
        elif rule_name == self._graph_engine.NAME_UNMATCHED:
            caption = unmatched_keys + ": unmatched keys"
            names = []
        else:
            caption = self._captions[rule_name]
            names = [rule_name]
            unmatched_skeys = ""
        xml = self._board_engine.from_rules(names, unmatched_skeys, board_ratio, compound=board_compound)
        return text, set_focus, rule_name, caption, xml

    def lexer_query(self, keys:str, letters:str, **kwargs) -> LexerResult:
        """ Return the best rule matching <keys> to <letters>. Thoroughly parse the key string into s-keys first. """
        skeys = self._layout.from_rtfcre(keys)
        return self._lexer.query(skeys, letters, **kwargs)

    def lexer_best_strokes(self, keys_iter:Iterable[str], letters:str) -> str:
        """ Return the best (most accurate) set of strokes from <keys_iter> that matches <letters>.
            Prefer shorter strokes over longer ones on ties. """
        keys_list = sorted(keys_iter, key=len)
        tr_list = [(self._layout.from_rtfcre(keys), letters) for keys in keys_list]
        best_index = self._lexer.find_best_translation(tr_list)
        return keys_list[best_index]

    def make_index(self, *args, **kwargs) -> Dict[str, _TR_DICT_TP]:
        """ Run the lexer on all <translations> with an input filter and look at the top-level rule names.
            Make a index containing a dict for each built-in rule with every translation that used it. """
        tr_filter = TranslationSizeFilter(*args)
        mapper = ParallelMapper(self._p_query, **kwargs)
        translations = self._search_engine.get_translations()
        translations = tr_filter.filter(translations)
        index = defaultdict(dict)
        for keys, letters, result in mapper.starmap(translations.items()):
            if not result.unmatched_skeys():
                # Add a translation to the index under the name of every rule in the result.
                for name in result.rules():
                    index[name][keys] = letters
        return index

    def _p_query(self, keys:str, letters:str) -> Tuple[str, str, LexerResult]:
        """ Make a lexer query and return the result in a tuple with its matching keys and letters.
            This is required for parallel operations where results may be returned out of order. """
        skeys = self._layout.from_rtfcre(keys)
        result = self._lexer.query(skeys, letters)
        return keys, letters, result


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
    mode_strokes: bool = False         # If True, search for strokes instead of translations.
    mode_regex: bool = False           # If True, perform search using regex characters.
    matches_per_page: int = 100        # Maximum number of matches returned on one page of a search.

    # Pure input values (display).
    board_aspect_ratio: float = 100.0  # Aspect ratio for board viewing area.
    board_compound: bool = True        # Show special labels for compound keys (i.e. `f` instead of TP).
    graph_compress: bool = True        # Compress the graph layout vertically to save space.
    graph_compat: bool = False         # Force correct spacing in the graph using HTML tables.
    match_all_keys: bool = False       # Only return lexer results that match every key in the stroke.

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
