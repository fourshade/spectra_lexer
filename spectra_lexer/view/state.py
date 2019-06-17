from spectra_lexer.types.codec import JSONDict


class ViewState(JSONDict):
    """ Contains a complete representation of the state of the GUI. """

    # The user may manipulate the GUI to change these values.
    action: str = ""                   # Last attempted action method name.
    input_text: str = ""               # Last pattern from user textbox input.
    match_selected: str = ""           # Last selected match from the upper list.
    mapping_selected: str = ""         # Last selected match from the lower list.
    mode_strokes: bool = False         # If True, search for strokes instead of translations.
    mode_regex: bool = False           # If True, perform search using regex characters.
    graph_location: list = None        # Last (row, col) character position on the graph.
    board_aspect_ratio: float = 100.0  # Last aspect ratio for board viewing area.

    # The user typically can't change these values directly. They are held for future reference.
    link_ref: str = ""                 # Name for the most recent rule with examples in the index
    match_count: int = 0               # Number of items in the upper list.
    graph_translation: list = None     # Currently diagrammed translation on graph.
    graph_has_selection: bool = False  # Is there a selected rule on the graph?

    # Pure output values.
    matches: list          # New items in the upper list.
    mappings: list         # New items in the lower list.
    graph_title: str       # New text in the title bar.
    graph_text: str        # HTML formatted text for the graph.
    board_caption: str     # Rule caption above the board.
    board_xml_data: bytes  # Raw XML data string for an SVG board.

    _changed: set  # Holds all attributes that were changed since creation.

    def __init__(self, *args, **kwargs):
        """ Allow item access through attributes. """
        super().__init__(*args, **kwargs)
        self.__dict__ = self
        self._changed = set()

    def __setattr__(self, attr:str, value) -> None:
        super().__setattr__(attr, value)
        if not attr.startswith("_"):
            self._changed.add(attr)

    def encode(self, *, encoding:str='utf-8', **kwargs) -> bytes:
        """ Encoding the state to JSON should only include relevant changes.
            Make sure all bytes objects are converted to normal strings for JSONification. """
        d = JSONDict()
        for k in self._changed:
            v = self[k]
            d[k] = v.decode(encoding) if isinstance(v, bytes) else v
        return d.encode(encoding=encoding, **kwargs)

    def do_updates(self, methods:dict) -> None:
        """ Given a dict of update methods by attribute, call each one whose attribute changed during processing. """
        for k in methods:
            if k in self._changed:
                methods[k](self[k])
