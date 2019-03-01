""" Base package for specific user interaction components. Without a GUI, these components do no good. """

from . import board, console, graph, search

COMPONENTS = [board.BoardRenderer,
              console.SpectraConsole,
              graph.GraphRenderer,
              search.SearchEngine]
