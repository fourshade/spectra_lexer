""" Master console script for the Spectra program. Contains all entry points. """

import sys

from spectra_lexer.core import Main
from spectra_lexer.gui_qt import GUIQtApplication
from spectra_lexer.plover import PloverPluginApplication
from spectra_lexer.steno import StenoApplication, StenoAnalyzeApplication, StenoIndexApplication

# Container for all app classes that qualify as entry points to the Spectra program.
ENTRY_POINTS = {"console": StenoApplication,
                "analyze": StenoAnalyzeApplication,
                "index":   StenoIndexApplication,
                "gui":     GUIQtApplication,
                "plugin":  PloverPluginApplication}

# With no arguments, redirect to the standalone GUI app.
main = Main(ENTRY_POINTS, default_mode="gui")

if __name__ == '__main__':
    sys.exit(main())
