from spectra_lexer.types.codec import CFGDict


class ConfigDictionary(CFGDict):

    OPTIONS = {"show_compound":    ("board", "compound_keys", True,
                                    "Show special labels for compound keys (i.e. `f` instead of TP)."),
               "recursive_graph":  ("graph", "recursive", True,
                                    "Include rules that make up other rules."),
               "compressed_graph": ("graph", "compressed", True,
                                    "Compress the graph vertically to save space."),
               "need_all_keys":    ("lexer", "need_all_keys", False,
                                    "Only return lexer results that match every key in the stroke."),
               "match_limit":      ("search", "match_limit", 100,
                                    "Maximum number of matches returned on one page of a search."),
               "show_links":       ("search", "example_links", True,
                                    "Show hyperlinks to other examples of a selected rule from an index.")}

    def __init__(self, *args, **kwargs):
        super().__init__()
        for sect, name, default, desc in self.OPTIONS.values():
            if sect not in self:
                self[sect] = {}
            self[sect][name] = default
        self.update(*args, **kwargs)

    def info(self) -> dict:
        info = {}
        for sect, name, default, desc in self.OPTIONS.values():
            v = self[sect][name]
            tp = type(v)
            label = name.replace("_", " ").title()
            if sect not in info:
                info[sect] = {}
            info[sect][name] = [v, tp, label, desc]
        return info

    def write_to(self, state:dict) -> None:
        d = self.OPTIONS
        for k in d:
            if k not in state:
                sect, name, _, _ = d[k]
                state[k] = self[sect][name]
