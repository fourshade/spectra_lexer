from typing import Dict, Tuple

from spectra_lexer import Component


class SVGManager(Component):
    """ SVG parser for the Spectra program. Used for the steno board diagram. """

    file = Resource("cmdline", "board-file", ":/board.svg", "SVG file with graphics for the steno board diagram.")

    @on("cmdline_opts_done", pipe_to="new_board")
    @on("board_load", pipe_to="new_board")
    def load(self, filename:str="") -> Tuple[str, Dict[str, dict]]:
        """ Load an SVG file and send the element ID names out with the raw XML string data. """
        d = self.engine_call("file_load", filename or self.file)
        return d["raw"], d["ids"]
