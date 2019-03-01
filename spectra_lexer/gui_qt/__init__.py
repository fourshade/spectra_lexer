""" Package for the GUI Qt-based components of Spectra. """

from . import board, config, console, file, graph, menu, search, window

COMPONENTS = [window.GUIQtWindow,
              menu.GUIQtMenu,
              file.GUIQtFileDialog,
              config.GUIQtConfigDialog,
              search.GUIQtSearchPanel,
              board.GUIQtBoardDisplay,
              graph.GUIQtTextDisplay,
              console.GUIQtConsoleDisplay]
