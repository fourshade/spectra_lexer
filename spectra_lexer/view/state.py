from spectra_lexer.types.codec import JSONDict


class ViewState(JSONDict):
    """ Contains a complete representation of the state of the GUI. """

    # The user may manipulate the GUI to change these values.
    input_text: str = ""               # Last pattern from user textbox input.
    match_selected: str = ""           # Last selected match from the upper list.
    mapping_selected: str = ""         # Last selected match from the lower list.
    mode_strokes: bool = False         # If True, search for strokes instead of translations.
    mode_regex: bool = False           # If True, perform search using regex characters.
    graph_location: list = None        # Last (row, col) character position on the graph.
    board_aspect_ratio: float = 100.0  # Last aspect ratio for board viewing area.

    # The user typically can't change these values directly.
    link_ref: str = ""                 # Name for the most recent rule with examples in the index
    matches: list = ()                 # Last items in the upper list.
    graph_translation: list = None     # Currently diagrammed translation on graph.
    graph_has_selection: bool = False  # Is there a selected rule on the graph?

    # Pure output values.
    mappings: list = ()                # Last items in the lower list.
    graph_title: str = ""              # The text in the title bar.
    graph_text: str = ""               # The HTML formatted text in the graph.
    board_caption: str = ""            # Show a caption above the board.
    board_xml_data: bytes = b""        # Render a raw XML data string as an SVG board.

    _changes: dict  # Holds all changes made since last iteration.

    def __init__(self, *args, **kwargs):
        """ Allow item access through attributes. """
        super().__init__(*args, **kwargs)
        self.__dict__ = self
        self._changes = {}

    def __setattr__(self, attr:str, value) -> None:
        super().__setattr__(attr, value)
        if not attr.startswith("_"):
            self._changes[attr] = value

    def __iter__(self):
        """ Yield every state attribute that was changed, then clear the dict. """
        yield from self._changes.items()
        self._changes = {}
