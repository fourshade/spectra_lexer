from typing import Dict

from spectra_lexer import Component


class SVGManager(Component):
    """ SVG parser for the Spectra program. Used for the steno board diagram. """

    file = Resource("cmdline", "board-file", ":/board.svg", "SVG file with graphics for the steno board diagram.")

    @on("load_dicts", pipe_to="set_dict_board")
    @on("board_load", pipe_to="set_dict_board")
    def load(self, filename:str="") -> Dict[str, dict]:
        """ Load an SVG file and send a dict with the raw XML string data and element ID names. """
        return self.engine_call("file_load", filename or self.file)
