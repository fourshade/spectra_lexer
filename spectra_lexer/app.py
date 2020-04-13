from typing import Any, Dict, Tuple

from spectra_lexer.engine import StenoEngine
from spectra_lexer.resource.config import Configuration
from spectra_lexer.search import SearchResults


class EngineOptions:
    """ Combined namespace for all steno engine options. """

    search_mode_strokes: bool = False       # If True, search for strokes instead of translations.
    search_mode_regex: bool = False         # If True, perform search using regex characters.
    search_match_limit: int = 100           # Maximum number of matches returned on one page of a search.
    lexer_strict_mode: bool = False         # Only return lexer results that match every key in a translation.
    board_aspect_ratio: float = None        # Aspect ratio for board viewing area (None means pure horizontal layout).
    board_show_compound: bool = True        # Show compound keys on board with alt labels (i.e. F instead of TP).
    board_show_letters: bool = True         # Show letters on board when possible. Letters override alt labels.
    graph_compressed_layout: bool = True    # Compress the graph layout vertically to save space.
    graph_compatibility_mode: bool = False  # Force correct spacing in the graph using HTML tables.

    # These user options are saved in a CFG file.
    CFG_OPTIONS = [("search_match_limit", 100, "Maximum number of matches returned on one page of a search."),
                   ("lexer_strict_mode", False, "Only return lexer results that match every key in a translation."),
                   ("graph_compressed_layout", True, "Compress the graph layout vertically to save space.")]


class DisplayPage:
    """ Data class that contains an HTML formatted graph, a caption, an SVG board, and a rule ID reference. """

    def __init__(self, graph:str, intense_graph:str, caption:str, board:str, rule_id="") -> None:
        self.graph = graph                  # HTML graph text for this selection.
        self.intense_graph = intense_graph  # Brighter HTML text graph for this selection.
        self.caption = caption              # Text characters drawn as a caption (possibly on a tooltip).
        self.board = board                  # XML string containing this rule's SVG board diagram.
        self.rule_id = rule_id              # If the selection uses a valid rule, its rule ID, else an empty string.


class DisplayData:
    """ Data class that contains graphical data for an entire analysis. """

    def __init__(self, keys:str, letters:str, pages:Dict[str, DisplayPage], default_page:DisplayPage) -> None:
        self.keys = keys                  # Translation keys in RTFCRE.
        self.letters = letters            # Translation letters.
        self.pages_by_ref = pages         # Analysis pages keyed by HTML anchor reference.
        self.default_page = default_page  # Default starting analysis page. May also be included in pages_by_ref.


class StenoGUIOutput:
    """ Data class that contains an entire GUI update. All fields are optional. """

    search_input: str = None              # Product of an example search action.
    search_results: SearchResults = None  # Product of a search action.
    display_data: DisplayData = None      # Product of a query action.


class StenoApplication:
    """ Common layer for user operations (resource I/O, GUI actions, analysis...it all goes through here). """

    def __init__(self, config:Configuration, engine:StenoEngine) -> None:
        self._config = config      # Keeps track of configuration options in a master dict.
        self._engine = engine      # Main steno analysis engine.
        self._index_filename = ""  # Holds filename for index; set on first load.
        for args in EngineOptions.CFG_OPTIONS:
            config.add_option(*args)

    def load_translations(self, *filenames:str) -> None:
        self._engine.load_translations(*filenames)

    def set_translations(self, *args) -> None:
        """ Send a new translations dict to the engine. """
        self._engine.set_translations(*args)

    def load_examples(self, filename:str) -> None:
        """ Load an examples index from a JSON file. Ignore file I/O errors since it may be missing. """
        self._index_filename = filename
        try:
            self._engine.load_examples(filename)
        except OSError:
            pass

    def load_config(self) -> bool:
        """ Load config settings from a CFG file. If the file is missing, start a new one and return True. """
        try:
            self._config.read()
            return False
        except OSError:
            self._config.write()
            return True

    def set_config(self, options:Dict[str, Any]) -> None:
        """ Update the config dict with <options> and save them back to the original CFG file. """
        self._config.update(options)
        self._config.write()

    def make_index(self, *args, **kwargs) -> None:
        """ Run the lexer on all <translations> with an input filter and look at the top-level rule names.
            Make an examples index containing a dict for each built-in rule with every translation that used it.
            Finish by setting them active and saving them to disk. """
        assert self._index_filename
        self._engine.compile_examples(*args, **kwargs)
        self._engine.save_examples(self._index_filename)

    def _with_config(self, options:dict) -> EngineOptions:
        """ Add config options first. The main <options> will override them. """
        opts = EngineOptions()
        vars(opts).update(self._config.to_dict())
        vars(opts).update(options)
        return opts

    def gui_query(self, translation:Tuple[str, str], *others:Tuple[str, str], **options) -> StenoGUIOutput:
        """ Execute and display a graph of a lexer query from search results or user strokes. """
        output = StenoGUIOutput()
        opts = self._with_config(options)
        strict_mode = opts.lexer_strict_mode
        if others:
            analysis = self._engine.analyze_best(translation, *others, strict_mode=strict_mode)
        else:
            analysis = self._engine.analyze(*translation, strict_mode=strict_mode)
        compressed = opts.graph_compressed_layout
        compat = opts.graph_compatibility_mode
        graph = self._engine.generate_graph(analysis, compressed, compat)
        aspect_ratio = opts.board_aspect_ratio
        show_compound = opts.board_show_compound
        show_letters = opts.board_show_letters
        pages = {}
        root_ref = None
        for ref in graph.refs():
            ngraph = graph.draw(ref)
            igraph = graph.draw(ref, intense=True)
            rule = graph.get_rule(ref)
            # Make a caption to display above the board diagram for this rule.
            if rule is analysis:
                # The root translation is in the title bar. Show only the info string in its caption.
                caption = rule.info
                root_ref = ref
            elif rule and rule.letters:
                # Compound rules show the complete mapping of keys to letters in their caption.
                caption = f'{rule}: {rule.info}'
            else:
                # Base rules display only their keys to the left of their descriptions.
                caption = f"{rule.keys}: {rule.info}"
            if show_compound:
                board = self._engine.generate_board(rule, aspect_ratio, show_letters)
            else:
                board = self._engine.generate_board_from_keys(rule.keys, aspect_ratio)
            # Remove links to any rules for which we don't have examples.
            r_id = rule.id if self._engine.has_examples(rule.id) else ""
            pages[ref] = DisplayPage(ngraph, igraph, caption, board, r_id)
        # When nothing is selected, use the board and caption for the root node.
        root_page = pages[root_ref]
        default_graph = graph.draw()
        default_page = DisplayPage(default_graph, default_graph, root_page.caption, root_page.board)
        output.display_data = DisplayData(analysis.keys, analysis.letters, pages, default_page)
        return output

    def gui_search(self, pattern:str, pages=1, **options) -> StenoGUIOutput:
        """ Do a new search and return results unless the input is blank. """
        output = StenoGUIOutput()
        opts = self._with_config(options)
        mode_strokes = opts.search_mode_strokes
        if pattern.strip():
            count = pages * opts.search_match_limit
            output.search_results = self._engine.search(pattern, count, mode_strokes, opts.search_mode_regex)
        return output

    def gui_search_examples(self, link_ref:str, **options) -> StenoGUIOutput:
        """ When a link is clicked, search for examples of the named rule and select one. """
        output = StenoGUIOutput()
        opts = self._with_config(options)
        mode_strokes = opts.search_mode_strokes
        keys, letters, pattern = self._engine.random_example(link_ref, mode_strokes)
        if keys and letters:
            output = self.gui_query((keys, letters), **options)
            output.search_input = pattern
            output.search_results = self._engine.search(pattern, opts.search_match_limit, mode_strokes)
        return output

    def console_vars(self) -> dict:
        """ Return a namespace with variables suitable for direct use in an interactive Python console. """
        ns = {}
        for obj in (self, self._engine):
            for k in dir(obj):
                if not k.startswith('_'):
                    ns[k] = getattr(obj, k)
        return ns
