from spectra_lexer.options import SpectraOptions
from spectra_lexer.resource.io import StenoResourceIO
from spectra_lexer.spc_board import BoardEngine, build_board_engine
from spectra_lexer.spc_graph import build_graph_engine, GraphEngine
from spectra_lexer.spc_lexer import build_analyzer, StenoAnalyzer
from spectra_lexer.spc_search import build_search_engine, SearchEngine
from spectra_lexer.util.log import open_logger, StreamLogger


class Spectra:
    """ Container for all common components, and the basis for using Spectra as a library. """

    def __init__(self, resource_io:StenoResourceIO, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 graph_engine:GraphEngine, board_engine:BoardEngine, logger:StreamLogger,
                 translations_paths:list, index_path:str, cfg_path:str) -> None:
        self.resource_io = resource_io
        self.search_engine = search_engine
        self.analyzer = analyzer
        self.graph_engine = graph_engine
        self.board_engine = board_engine
        self.logger = logger
        self.translations_paths = translations_paths
        self.index_path = index_path
        self.cfg_path = cfg_path

    @classmethod
    def compile(cls, opts:SpectraOptions=None, *, parse_args=True) -> 'Spectra':
        """ From command-line options, load and verify each resource component, then return the complete collection. """
        if opts is None:
            opts = SpectraOptions()
        if parse_args:
            opts.parse()
        r_io = StenoResourceIO()
        keymap_path = opts.keymap_path()
        keymap = r_io.load_keymap(keymap_path)
        keymap.verify()
        rules_path = opts.rules_path()
        rules = r_io.load_rules(rules_path)
        valid_rtfcre = keymap.valid_rtfcre()
        delimiters = {keymap.separator_key(), keymap.divider_key()}
        for rule in rules:
            rule.verify(valid_rtfcre, delimiters)
        board_defs_path = opts.board_defs_path()
        board_defs = r_io.load_board_defs(board_defs_path)
        board_defs.verify()
        search_engine = build_search_engine(keymap)
        analyzer = build_analyzer(keymap, rules)
        graph_engine = build_graph_engine(keymap)
        board_engine = build_board_engine(keymap, board_defs)
        log_path = opts.log_path()
        logger = open_logger(log_path, to_stdout=True)
        translations_paths = opts.translations_paths()
        index_path = opts.index_path()
        cfg_path = opts.config_path()
        return Spectra(r_io, search_engine, analyzer, graph_engine, board_engine,
                       logger, translations_paths, index_path, cfg_path)
