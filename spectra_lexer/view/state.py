class ViewState:
    """ Contains a complete representation of the state of the GUI. """

    # The user may manipulate the GUI to change these values.
    input_text: str = ""               # Last pattern from user textbox input.
    match_selected: str = ""           # Last selected match from the upper list.
    mapping_selected: str = ""         # Last selected match from the lower list.
    mode_strokes: bool = False         # If True, search for strokes instead of translations.
    mode_regex: bool = False           # If True, perform search using regex characters.
    translation: str = ""              # String form of currently diagrammed translation on graph.
    graph_node_ref: str = ""           # Last node identifier on the graph ("" for empty space).
    board_aspect_ratio: float = 100.0  # Last aspect ratio for board viewing area.

    # The user typically can't change these values directly. They are held for future reference.
    link_ref: str = ""                 # Name for the most recent rule (if there are examples in the index).
    match_count: int = 0               # Number of items in the upper list.
    graph_has_selection: bool = False  # Is there a selected rule on the graph?

    # Pure output values.
    matches: list = []           # New items in the upper list.
    mappings: list = []          # New items in the lower list.
    graph_text: str = ""         # HTML formatted text for the graph.
    board_caption: str = ""      # Rule caption above the board.
    board_xml_data: bytes = b""  # Raw XML data string for an SVG board.

    _changed: dict  # Holds all attributes and values that were changed since creation.

    def __init__(self, *args, **kwargs):
        """ Update attribute dict directly with any args. """
        self.__dict__.update(*args, **kwargs, _changed={})

    def __setattr__(self, attr:str, value) -> None:
        """ Add any modified public attributes to the change dict. """
        super().__setattr__(attr, value)
        if not attr.startswith("_"):
            self._changed[attr] = value

    def changed(self) -> dict:
        """ Return all items that have been changed since creation in a dict. """
        return self._changed

    def get_query_params(self) -> tuple:
        """ Return query parameters from the translation string, or None if there aren't enough. """
        params = (*map(str.strip, self.translation.split('->', 1)),)
        if len(params) == 2 and all(params):
            return params

    def set_query_params(self, keys:str, letters:str) -> None:
        """ Set the translation string from query parameters. """
        self.translation = f'{keys} -> {letters}'
